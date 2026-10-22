"""Executable rule checks, one-action probes, and feedback in the real action path."""
from __future__ import annotations
import ast
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import time

PROMPT = '''Executable rule experiments are available through rule_lab. When a simulator contradicts observations, two explanations predict different outcomes, or a level stalls, encode the disputed visible state and test it against actual history before doing a long search. Separate observed pixels from object/goal interpretations. Define pure observe(frame) and named predict(state, action) functions, then RULES={"name": predict}. observe may use frame.ascii, frame.shape and frame.segmentation; action is a dict such as {"action":"RIGHT"} or {"action":"MOUSE","row":12,"col":5}. Each predictor returns {"state": next_encoded_state}, optionally with boolean game_over and level_completed; return None only for genuinely unsupported actions. Outcome flags are checked against real completion/death signals. Use self-contained definitions and literal constants, without history/current_frame/action calls inside the program. The tool replays observations, reports exact counterexamples, and retains only non-refuted candidates for this level. Consistency on a partial state is not proof of a whole-game rule.
With two alternatives, provide up to 12 legal candidate actions and execute_probe=true to search up to two moves for disagreement. The tool executes at most the first move through the ordinary game executor, rechecks the actual outcome, and returns surviving/refuted rules. Recheck the new observation before a second probe. Predictions of safety are fallible. Do not spend probes on identical predictions. Registered rules are automatically checked on later Python actions; contradictions interrupt the remaining batch and return the real counterexample. Correct the definitions and resubmit rule_lab, or mode="clear" with a reason when the representation no longer applies. Straightforward actions need no rule program.'''

TOOL = {'type':'function','function':{'name':'rule_lab','description':PROMPT,
    'parameters':{'type':'object','properties':{
        'program':{'type':'string','description':'Self-contained pure observe(frame), prediction functions, and RULES mapping. Omit to reuse the active program.'},
        'actions':{'type':'array','items':{'type':'object','properties':{'action':{'type':'string'},'row':{'type':'integer'},'col':{'type':'integer'}},'required':['action']},'description':'Candidate real actions whose consequences you are willing to inspect; no RESET.'},
        'execute_probe':{'type':'boolean','description':'Execute at most one selected discriminating/preparatory action after checks. Default false.'},
        'mode':{'type':'string','enum':['check','clear']},
        'reason':{'type':'string'}},'required':[]}}}


@dataclass
class State:
    scope: str
    level: int
    program: str = ''
    names: list = field(default_factory=list)
    active: list = field(default_factory=list)
    worker: object = None
    nudged: bool = False
    pending_notice: str = ''
    delivered_notice: str = ''
    checks: int = 0
    probes: int = 0


def current(agent, path):
    from inference.agent.runtime_state import load_runtime_state
    frame, history = load_runtime_state(path)
    if frame is None:
        raise ValueError('Current frame unavailable')
    scope = str(Path(path).parent)
    state = getattr(agent, '_rule_lab_state', None)
    if state is None or state.scope != scope or state.level != frame.level:
        if state is not None and state.worker is not None:
            state.worker.close()
        state = agent._rule_lab_state = State(scope, frame.level)
    return state, frame, history


def audit(path, kind, **values):
    try:
        with (Path(path).parent/'rule_lab.jsonl').open('a',encoding='utf-8') as handle:
            handle.write(json.dumps(dict(kind=kind, **values),ensure_ascii=False)+'\n')
    except OSError:
        pass


def validate_program(program):
    if not isinstance(program,str) or not 1 <= len(program) <= 20000:
        raise ValueError('Provide a self-contained rule program of at most 20000 characters')
    tree = ast.parse(program)
    definitions = {node.name for node in tree.body if isinstance(node,ast.FunctionDef)}
    if 'observe' not in definitions:
        raise ValueError('Define observe(frame)')
    rules = None
    modules = {'copy','json','math','re','collections','itertools','functools','heapq','bisect','statistics','fractions','operator'}
    forbidden = {'current_frame','previous_frame','history','transitions','last_transition','valid_actions',
                 'latest_frame','last_action','last_action_call_result','action','last_animation_frames',
                 'last_animation_timeline','globals','locals','vars','eval','exec','getattr','setattr',
                 'delattr','__import__','open','input','compile'}
    # "action" is permitted as a predictor parameter; calling it is not.
    forbidden.remove('action')
    for node in ast.walk(tree):
        if isinstance(node,ast.Name) and (node.id in forbidden or node.id.startswith(('rl_','_rl_','__'))):
            raise ValueError('Rules must use their arguments, not runtime observations: '+node.id)
        if isinstance(node,ast.Attribute) and node.attr.startswith('_'):
            raise ValueError('Use public frame properties, not private attributes')
        if isinstance(node,(ast.Global,ast.Nonlocal,ast.ClassDef,ast.AsyncFunctionDef)):
            raise ValueError('Use pure ordinary functions')
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='action':
            raise ValueError('Rule programs cannot execute game actions')
        if isinstance(node,ast.Import):
            if any(alias.name not in modules for alias in node.names):
                raise ValueError('Unsupported or nondeterministic import')
        if isinstance(node,ast.ImportFrom) and (node.level or node.module not in modules):
            raise ValueError('Unsupported import')
    for node in tree.body:
        if isinstance(node,(ast.FunctionDef,ast.Import,ast.ImportFrom)):
            if isinstance(node,ast.FunctionDef) and (node.decorator_list or node.args.defaults or node.args.kw_defaults):
                raise ValueError('Use functions without decorators/default expressions')
            continue
        if isinstance(node,ast.Expr) and isinstance(node.value,ast.Constant) and isinstance(node.value.value,str):
            continue
        if not isinstance(node,ast.Assign) or len(node.targets)!=1 or not isinstance(node.targets[0],ast.Name):
            raise ValueError('Top level allows only function definitions, imports and literal constants')
        name=node.targets[0].id
        if name=='RULES':
            if rules is not None or not isinstance(node.value,ast.Dict):
                raise ValueError('Define RULES once as a literal mapping of names to functions')
            rules={}
            for key,value in zip(node.value.keys,node.value.values):
                label=ast.literal_eval(key)
                if not isinstance(label,str) or not 1<=len(label)<=60 or not isinstance(value,ast.Name) or value.id not in definitions:
                    raise ValueError('RULES values must be named functions')
                if label in rules:
                    raise ValueError('Duplicate rule name')
                rules[label]=value.id
        else:
            ast.literal_eval(node.value)
    if not rules or len(rules)>4:
        raise ValueError('Define one to four named RULES')
    return list(rules)


def snapshot(agent, path, *, recent_from=None):
    from inference.agent.runtime_state import load_runtime_state
    from inference.agent.tool_agent import _ascii_frame_view_payload, _ascii_history_view_payload
    frame, history = load_runtime_state(path)
    if recent_from is not None:
        history = history[max(0,recent_from-1):]
    return dict(current_frame=_ascii_frame_view_payload(frame),history=_ascii_history_view_payload(history),
                valid_actions=list(agent._current_valid_actions),last_action_call_result=dict(agent._last_action_call_result or {}))


def compute(state, payload, expression):
    from inference.agent.rule_lab_python import LevelPython
    if state.worker is None:
        state.worker=LevelPython()
    source=Path(__file__).with_name('rule_lab_eval.py').read_text(encoding='utf-8')
    def deny(*args,**kwargs):
        return dict(action_result=dict(executed=False,executed_count=0,error='Rule verification is read-only'),state=payload)
    output=state.worker.run(scope=state.scope+'/rule_lab',code=source+'\n'+state.program+'\nresult = '+expression,
        timeout_seconds=5,initial_state=payload,action_handler=deny,kept_functions=[],retain_imports=False)
    if output.get('error') or not isinstance(output.get('result'),dict):
        raise ValueError(str(output.get('error') or 'Rule check returned no structured result')[:1000])
    return output['result']


def survivors(report):
    return [name for name, item in report['rules'].items() if not item['mismatched'] and not item['errors']]


def normalize_candidates(agent, actions, frame):
    from inference.agent.action_names import to_engine_action, to_model_action
    if not isinstance(actions,list) or len(actions)>12:
        raise ValueError('Provide at most 12 candidate actions')
    valid={to_engine_action(a) for a in agent._current_valid_actions}-{None}
    result=[]
    for action in agent._normalize_python_actions(actions) if actions else []:
        action['action']=to_model_action(action['action'])
        if to_engine_action(action['action'])=='RESET' or to_engine_action(action['action']) not in valid:
            raise ValueError('Probe action is not currently legal: '+str(action))
        if action['action']=='MOUSE' and (any(type(action.get(k)) is not int for k in ('row','col')) or not (0<=action['row']<frame.shape[0] and 0<=action['col']<frame.shape[1])):
            raise ValueError('Probe coordinates are outside the actual frame')
        if action not in result:
            result.append(action)
    return result


def dispatch(agent, path, arguments):
    from inference.agent.tool_agent import _ToolDispatchResult
    state, frame, history=current(agent,path)
    executed = None
    try:
        arguments=dict(arguments)
        for key in ('actions','execute_probe'):
            if isinstance(arguments.get(key),str):
                arguments[key]=json.loads(arguments[key])
        if 'execute_probe' in arguments and type(arguments['execute_probe']) is not bool:
            raise ValueError('execute_probe must be a boolean')
        if arguments.get('mode','check') not in ('check','clear'):
            raise ValueError('mode must be check or clear')
        if arguments.get('mode')=='clear':
            reason=str(arguments.get('reason') or '').strip()
            if not reason:
                raise ValueError('Explain why these rules no longer apply')
            state.program='';state.names=[];state.active=[];state.pending_notice=''
            if state.worker:state.worker.close()
            audit(path,'clear',level=frame.level,reason=reason[:1000])
            return _ToolDispatchResult(json.dumps(dict(cleared=True,reason=reason)))
        program=arguments.get('program') or state.program
        names=validate_program(program)
        actions=normalize_candidates(agent,arguments.get('actions') or [],frame)
        state.program=program;state.names=names;state.active=[]
        payload=snapshot(agent,path)
        report=compute(state,payload,f'rl_check({names!r}, {frame.level!r})')
        state.active=survivors(report);state.checks+=1
        state.pending_notice=''
        report.update(active_rules=state.active,program_sha256=hashlib.sha256(program.encode()).hexdigest(),
                      level=frame.level,step=frame.step,real_actions_executed=0)
        search=compute(state,payload,f'rl_probes({state.active!r}, {actions!r})') if actions else {'probes':[]}
        report['probe_search']=search
        audit(path,'register',**report)
        if arguments.get('execute_probe') and search['probes']:
            chosen=search['probes'][0]
            # Bind execution to the exact observation used for selecting the probe.
            _, fresh, _=current(agent,path)
            if fresh.level!=frame.level or fresh.step!=frame.step:
                raise ValueError('State changed while computing the probe; no action was executed')
            first=chosen['actions'][0]
            executed=agent._run_python_tool(path,{'code':'result = action('+repr([first])+')'})
            state.probes+=int(executed.step_executed)
            report['selected_probe']=chosen
            report['real_actions_executed']=int(executed.step_executed)
            report['execution']=json.loads(executed.content)
            report['instruction']='Inspect the real counterexample/survivors. Any remaining actions are predictions only and have not executed. Correct the rule or recompute the next probe from the new frame.'
            audit(path,'probe',level=frame.level,step=frame.step,action=first,executed=executed.step_executed,active_rules=state.active)
            return _ToolDispatchResult(json.dumps(report,ensure_ascii=False),step_executed=executed.step_executed,made_progress=executed.made_progress)
        if arguments.get('execute_probe'):
            report['instruction']='No informative eligible probe found; no action executed. Check the representation, correct contradicted models, or supply genuinely different alternatives/actions.'
        return _ToolDispatchResult(json.dumps(report,ensure_ascii=False))
    except Exception as exc:
        audit(path,'tool_error',level=frame.level,error=str(exc)[:1000])
        from inference.agent.runtime_state import load_runtime_state
        _,latest_history=load_runtime_state(path)
        actual=sum(bool(item.action) and not (item.result or {}).get('automatic') for item in latest_history[len(history):])
        happened = bool(actual or (executed is not None and executed.step_executed))
        error = dict(error=type(exc).__name__+': '+str(exc)[:1500],real_actions_executed=actual)
        if executed is not None:
            error['execution'] = executed.content
        return _ToolDispatchResult(json.dumps(error),step_executed=happened,
                                   made_progress=bool(executed is not None and executed.made_progress))


def guarded_actions(agent, path, execute):
    def call(actions, *, stale_after=None):
        existing=getattr(agent,'_rule_lab_state',None)
        if existing is None or not existing.program or not existing.active:
            return execute(actions,stale_after=stale_after)
        state, frame, _=current(agent,path)
        if not state.program or not state.active:
            return execute(actions,stale_after=stale_after)
        normalized=agent._normalize_python_actions(actions)
        from inference.agent.action_names import to_engine_action,to_model_action
        for action in normalized:action['action']=to_model_action(action['action'])
        started=time.monotonic();total=0;feedback=[];displays=[];changed=False;animations=[]
        result=None
        for index,action in enumerate(normalized):
            from inference.agent.runtime_state import load_runtime_state
            before,history=load_runtime_state(path)
            names=list(state.active)
            try:
                predictions=compute(state,snapshot(agent,path,recent_from=len(history)),f'rl_predictions({names!r}, {action!r})')
            except Exception as exc:
                state.active=[]
                if result is None:
                    result=execute(normalized,stale_after=stale_after)
                    result['action_result']['rule_feedback']={'checker_unavailable':str(exc)[:500],'scope':'Original action execution retained; no rule claim.'}
                    return result
                result['action_result']['rule_interrupt']=True
                result['action_result']['stop_detail']='Rule checker unavailable; inspect the updated frame before continuing.'
                break
            # Every real action uses the original executor exactly once.
            # Preserve the original fatal-prefix lookahead and its override
            # across a checked batch split into one real move at a time.
            agent._rule_lab_guard_remaining=[(to_engine_action(a['action']),{k:v for k,v in a.items() if k!='action'}) for a in normalized[index:]]
            agent._rule_lab_continue_guard=index>0
            try:
                result=execute([action],stale_after=stale_after if index==0 else None)
            finally:
                agent._rule_lab_guard_remaining=None
                agent._rule_lab_continue_guard=False
            outcome=result['action_result'];count=int(outcome.get('executed_count') or int(bool(outcome.get('executed'))))
            total+=count;changed|=bool(outcome.get('gameplay_changed'))
            displays.extend(outcome.get('executed_actions') or [])
            animations.extend(getattr(agent,'_last_animation_chain',[]) or [])
            if not count:
                break
            try:
                report=compute(state,snapshot(agent,path,recent_from=len(history)),f'rl_check({names!r}, {before.level!r}, minimum_step={before.step!r})')
                state.active=survivors(report)
                rejected=[name for name in names if name not in state.active]
                terminal=bool(outcome.get('game_over') or outcome.get('level_completed') or outcome.get('run_complete') or outcome.get('done'))
                unknown=[name for name,item in report['rules'].items() if not item['checked']]
                event=dict(step=outcome.get('action_num'),action=action,rules=report['rules'],active_rules=state.active,
                           rejected_rules=rejected,unsupported_rules=unknown,prediction_errors=predictions['errors'])
                feedback.append(event);audit(path,'action_check',level=before.level,**event)
                if rejected or predictions['errors'] or unknown:
                    state.pending_notice='A real action has contradicted or exceeded the registered rule model. Read the rule_feedback counterexample, correct the affected definitions or explicitly clear a representation that no longer applies. Preserve valid observations and prior successful rules.'
                    outcome['rule_interrupt']=True
                    outcome['stop_detail']=json.dumps(event,ensure_ascii=False)[:4500]
                if terminal:
                    state.active=[]
                if outcome.get('rule_interrupt') or terminal or outcome.get('stopped_early') or time.monotonic()-started>12:
                    if not terminal and not outcome.get('rule_interrupt') and index<len(normalized)-1:
                        outcome['rule_interrupt']=True;outcome['stop_detail']='Rule checking reached its per-call time budget; inspect completed actions before continuing.'
                    break
            except Exception as exc:
                # The action already happened. Never repeat it after a check failure.
                state.active=[]
                outcome['rule_interrupt']=True
                outcome['stop_detail']='Action executed; post-action check failed: '+str(exc)[:500]+'. Inspect the real frame; no action will be replayed.'
                break
        outcome=result['action_result']
        outcome.update(executed=total>0,executed_count=total,requested_count=len(normalized),gameplay_changed=changed,
                       rule_feedback=feedback,executed_actions=displays)
        if total<len(normalized):outcome['stopped_early']=True
        result['state']['last_action_call_result']=dict(outcome)
        agent._last_action_call_result=dict(outcome)
        agent._last_animation_chain=animations
        return result
    return call


def notice(agent,path):
    tokens=max(0,agent._session_generated_tokens-getattr(agent,'_tokens_at_level_start',0))
    existing=getattr(agent,'_rule_lab_state',None)
    if tokens<16384 and not (existing and existing.pending_notice):
        return ''
    state,frame,history=current(agent,path)
    if not state.pending_notice and not state.nudged and tokens>=16384:
        state.nudged=True
        state.pending_notice='This level has consumed 16384 generated tokens. Before more long planning, isolate one disputed reading/transition/goal, express the competing explanations in rule_lab, and test them against actual observations. Use an informative probe only if the predictions differ. Do not invent alternatives just to satisfy the tool; a small exact-pixel inspection is appropriate when the uncertainty is a reading error.'
    state.delivered_notice=state.pending_notice
    return state.pending_notice


def acknowledge(agent,path):
    state,_,_=current(agent,path)
    if state.pending_notice==state.delivered_notice:
        state.pending_notice=''

