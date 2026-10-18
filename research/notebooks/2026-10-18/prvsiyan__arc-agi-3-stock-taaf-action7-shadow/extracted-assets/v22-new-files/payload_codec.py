"""Decode only source literals; never execute a historical notebook launcher."""
import ast
import base64
import hashlib
import json
import zlib

LAYERS = [
    (110, '14b08666c9b8f8cd82306d0f12393030940c8aa3d6a95654e42a790d51fd9411',
     '27c411fa314bb9e82fb35f80ab6984bdedccaa5223e0b7f6e776aa9614940fe4',
     '553e3e56a4d55e92ea3f5cdbd473b126da923e9ce4a7c29b35747bee919cdd0e'),
    (112, '34502f740ec7d81d5b74e98111f5b495e3695391e243a897140adc0d9e93435a',
     'a004b43a878971e741fcd6b8360d173c08f7a08b75a86b4d05502e0330866ec1',
     '23d8e531d27238017e6f147361ad87b9234b843f9c0512841ffc8b6b4634f4f0'),
    (114, '746bbf5a3274473bcd1ca4ea0e788b54bf7ff436a5e8cafe811e89517366274b',
     '73b7ff26b41d0a0c08418f0cca696ebf0b3d3e6892799230c894dfa1779a8899',
     '44272820c4af24a4d35e44adf9ded49a233e554f0dcb8799abc50b936846674f'),
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def text(cell):
    return ''.join(cell['source']) if isinstance(cell['source'], list) else cell['source']


def unpack(encoded):
    raw = base64.b64decode(encoded, validate=True)
    require(len(raw) <= 1000000, 'COMPRESSED_SOURCE_BOUND_EXCEEDED')
    decoder = zlib.decompressobj()
    payload = decoder.decompress(raw, 2000000)
    require(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail,
            'SOURCE_DECOMPRESSION_BOUND_OR_FORMAT_FAILED')
    return raw, payload


def assignments(source):
    return {n.targets[0].id: n.value for n in ast.parse(source).body
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)}


def unwrap(cell):
    tree = ast.parse(text(cell))
    require(len(tree.body) == 1 and isinstance(tree.body[0], ast.Assign), 'HISTORICAL_CELL_NOT_INERT')
    preserved = ast.literal_eval(tree.body[0].value)
    require(preserved['encoding'] == 'zlib+base64', 'PRESERVATION_ENCODING_DRIFT')
    _, source = unpack(preserved['data'])
    require(sha(source) == preserved['utf8_sha256'], 'LOSSLESS_HISTORY_DRIFT')
    return source


def decode_sources(notebook, *, full):
    require(len(notebook['cells']) == (117 if full else 115), 'NOTEBOOK_SHAPE_DRIFT')
    sources = {}
    for index, source_sha, compressed_sha, payload_sha in LAYERS:
        source = unwrap(notebook['cells'][index]) if index != 114 or full else text(notebook['cells'][index]).encode()
        require(sha(source) == source_sha, 'PINNED_HISTORICAL_SOURCE_DRIFT')
        values = assignments(source)
        raw, payload = unpack(ast.literal_eval(values['_compressed'].args[0]))
        require(sha(raw) == compressed_sha and sha(payload) == payload_sha, 'PINNED_HISTORICAL_PAYLOAD_DRIFT')
        if index == 114:
            patch = 'prepared_v1/harness-changes.patch'
            require(ast.literal_eval(values['_patch_suffix']) == '\n'
                    and sha(sources[patch].encode()) == '07fd859e7ce7ad8ac8a2f8f726d862660c1be1abc97560a63b5985703ddf7f4f',
                    'EXACT_LF_REPAIR_BINDING_DRIFT')
            sources[patch] += '\n'
            require(sha(sources[patch].encode()) == '80aef535ee80970622127f3ee1917e1b127db22ebe07ece40fc8558a63b4484d',
                    'CORRECTED_PATCH_DRIFT')
        sources.update(json.loads(payload))
        require({n: sha(s.encode()) for n, s in sources.items()} == ast.literal_eval(values['_hashes']),
                'HISTORICAL_MEMBER_HASH_DRIFT')
    if full:
        values = assignments(text(notebook['cells'][-1]))
        _, payload = unpack(ast.literal_eval(values['_compressed'].args[0]))
        sources.update(json.loads(payload))
        require({n: sha(s.encode()) for n, s in sources.items()} == ast.literal_eval(values['_hashes']),
                'FULL_OVERLAY_MEMBER_HASH_DRIFT')
    return sources


def verify_preservation(original, candidate):
    require(len(original['cells']) == 115 and len(candidate['cells']) == 117, 'PRESERVATION_SHAPE_DRIFT')
    require({k:v for k,v in original.items() if k != 'cells'} ==
            {k:v for k,v in candidate.items() if k != 'cells'}, 'NOTEBOOK_TOP_METADATA_DRIFT')
    require(original['cells'][:114] == candidate['cells'][:114], 'HISTORY_OR_ART_DRIFT')
    require({k:v for k,v in original['cells'][114].items() if k != 'source'} ==
            {k:v for k,v in candidate['cells'][114].items() if k != 'source'}, 'PRIOR_CELL_METADATA_DRIFT')
    require(unwrap(candidate['cells'][114]) == text(original['cells'][114]).encode(), 'PRIOR_LAUNCHER_TEXT_NOT_PRESERVED')
