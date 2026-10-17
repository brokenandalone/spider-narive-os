"""Dev Bay: source diagnostics with AST and dependency previews; never execute code."""
from __future__ import annotations
import ast
from collections import Counter,defaultdict
from .max_core import *
EXT={'.py','.js','.ts','.sh','.css','.html','.json','.toml','.yaml','.yml','.txt','.cfg'}

def run(action,root,query=''):
    root=selected(root);sources=list(text_records(root,EXT));data={}
    if action=='repository-map':data={'files':len(sources),'extensions':dict(Counter(Path(n).suffix for n,_ in sources)),'lines':sum(t.count('\n')+1 for _,t in sources)}
    elif action in ('python-ast','python-functions','python-imports'):
        records=[]
        for name,t in sources:
            if not name.endswith('.py'):continue
            try:tree=ast.parse(t)
            except (SyntaxError,ValueError):records.append({'file':name,'parse':'FAILED'});continue
            row={'file':name,'classes':sum(isinstance(n,ast.ClassDef) for n in ast.walk(tree)),
                 'functions':sum(isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) for n in ast.walk(tree)),
                 'imports':sorted(set(a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names)|set((n.module or '').split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.ImportFrom))),
                 'lines':t.count('\n')+1}
            records.append(row)
        if action=='python-imports':data={'imports':[{ 'file':r['file'],'modules':r.get('imports',[])} for r in records[:130]]}
        elif action=='python-functions':data={'functions':[{ 'file':r['file'],'functions':r.get('functions',0),'classes':r.get('classes',0)} for r in records[:130]]}
        else:data={'files':records[:160]}
    elif action=='test-coverage-map':
        data={'test_files':[n for n,t in sources if re.search(r'(^|/)test_[^/]+\.py$',n) or n.endswith('_test.py')][:150],
              'source_modules':len([n for n,t in sources if n.endswith('.py') and '/test_' not in n])}
    elif action=='todo-ledger':
        data={'items':[{'file':n,'line':i,'text':quote_prefix(line,160)} for n,t in sources for i,line in enumerate(t.splitlines(),1) if re.search(r'\b(?:TODO|FIXME|XXX|HACK)\b',line)][:140]}
    elif action=='large-modules':
        data={'files':sorted(({'file':n,'lines':t.count('\n')+1} for n,t in sources),key=lambda x:x['lines'],reverse=True)[:65]}
    elif action=='risky-code-locations':
        pat=re.compile(r'\b(?:os\.system\s*\(|shell\s*=\s*True|eval\s*\(|exec\s*\(|pickle\.loads\s*\(|chmod\s+777)')
        data={'locations':[{'file':n,'line':i,'pattern':next((k for k in ('os.system','shell','eval','exec','pickle','chmod') if k in line),'other')} for n,t in sources for i,line in enumerate(t.splitlines(),1) if pat.search(line)][:100], 'no_source_values_returned':True}
    elif action=='package-file-review':
        data={'manifests':[n for n,t in sources if Path(n).name in ('pyproject.toml','requirements.txt','package.json','setup.cfg','Cargo.toml','go.mod','Pipfile','poetry.lock')],'note':'No package manager invoked.'}
    elif action=='documentation-map':
        data={'docs':[n for n,t in sources if Path(n).suffix in ('.md','.html')][:130]}
    else:raise ValueError('Unsupported Dev operation')
    return standard_result('Dev Bay',action,root,data)
ACTIONS=('repository-map','python-ast','python-functions','python-imports','test-coverage-map','todo-ledger','large-modules','risky-code-locations','package-file-review','documentation-map')
