"""Synthetic harness-source probe; no model snippets, game engines, or network.

This isolates summary construction and the existing accounting block. It does
not instantiate ToolAgent or certify the live call chain.
"""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).parent
source=ROOT/'research/runtime-bundle/src/ARC3-Inference/inference/agent/tool_agent.py'
priority=source.with_name('priority_scheduler.py')
spec=importlib.util.spec_from_file_location('arc3_pace_probe',priority)
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
tree=ast.parse(source.read_text())
cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ToolAgent')
methods={n.name:n for n in cls.body if isinstance(n,ast.FunctionDef)}
summary=copy.deepcopy(methods['_summarize_step_sequence'])
update=copy.deepcopy(methods['_update_summarized_knowledge_from_step_summary'])
# Keep the original body through the first level-transition accounting branch.
end=next(i for i,n in enumerate(update.body) if isinstance(n,ast.If)
         and isinstance(n.test,ast.Call) and ast.unparse(n.test)=="summary.get('level_transition')")
update.body=update.body[:end+1]
terminal=copy.deepcopy(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_terminal_action_reason'))
reference=json.loads(priority.with_name('priority_pace_reference.json').read_text())
namespace={'Any':Any,'_get_env_bool':lambda *a: True,
           '_pace_reference_tokens':lambda level:reference['by_level'].get(str(level),reference['fallback_tokens']),
           '_priority_action_count':lambda s:int(s.get('end_action_num') or 0)}
future=ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)
exec(compile(ast.fix_missing_locations(ast.Module(body=[future,summary,update,terminal],type_ignores=[])),str(source),'exec'),namespace)
def agent(tokens):
    return SimpleNamespace(_last_step_summary=None,_session_generated_tokens=tokens,
         _tokens_at_level_start=0,_actions_at_level_start=0,_pace_last_completed_level=0,
         _progress_pace=m.ProgressPace())
def payload(level,number):
    return dict(executed=True,executed_count=1,level=level,action_num=number,
                level_completed=True,action_display='synthetic',executed_actions=['synthetic'])
checks=[]
a=agent(reference['by_level']['1'])
a._last_step_summary=namespace['_summarize_step_sequence'](a,[payload(2,1)])
namespace['_update_summarized_knowledge_from_step_summary'](a)
checks.append({'name':'one_transition_records_one_reference_cost','passed':a._progress_pace.completed==1 and a._progress_pace.cost_multiplier()==1})
a._session_generated_tokens+=reference['by_level']['2']
a._last_step_summary=namespace['_summarize_step_sequence'](a,[payload(3,2)])
namespace['_update_summarized_knowledge_from_step_summary'](a)
checks.append({'name':'next_transition_records_second_reference_cost','passed':a._progress_pace.completed==2 and a._progress_pace.cost_multiplier()==1})
b=agent(reference['by_level']['1']+reference['by_level']['2'])
synthetic_multi=[payload(2,1),payload(3,2)]
b._last_step_summary=namespace['_summarize_step_sequence'](b,synthetic_multi)
namespace['_update_summarized_knowledge_from_step_summary'](b)
checks.append({'name':'artificial_two_transition_summary_is_one_record','passed':b._progress_pace.completed==1 and b._pace_last_completed_level==2,
               'semantic_boundary':'Artificial malformed caller input; normal action batch and snippet terminal guards prevent this sequence.'})
checks.append({'name':'level_completed_is_terminal_for_host','passed':namespace['_terminal_action_reason'](payload(2,1))=='level_completed'})
assert all(c['passed'] for c in checks)
result={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'kind':'synthetic_extracted_summary_and_accounting_block_not_live_toolagent_validation',
        'checks':checks,'artificial_multi_summary':b._last_step_summary,
        'artificial_multi_recorded_completed_count':b._progress_pace.completed,
        'artificial_multi_multiplier':b._progress_pace.cost_multiplier(),
        'normal_path_static_guards':['inference/framework/solver.py:1118-1126 stops batch at first level completion',
                                    'inference/agent/tool_agent.py:5784-5810 refuses further snippet actions after terminal result',
                                    'inference/agent/python_tool_sandbox.py:490 and :534-540 latch level completion'],
        'limitations':['Did not instantiate full ToolAgent, invoke sandbox, or validate live session usage ledger.',
                       'Synthetic multi-transition input is not evidence of a production-reachable bug.',
                       'No model, game action, engine source, logged code execution, network or GPU.']}
(OUT/'pace-contract-probe.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'checks':checks,'kind':result['kind']},indent=2))
