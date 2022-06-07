# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/01_read.ipynb.

# %% auto 0
__all__ = ['mk_cell', 'create_output', 'NBRunner', 'nbprocess_create_config', 'get_config', 'config_key', 'add_init',
           'write_cells', 'basic_export_nb']

# %% ../nbs/01_read.ipynb 3
from datetime import datetime
from fastcore.imports import *
from fastcore.foundation import *
from fastcore.utils import *
from fastcore.test import *
from fastcore.script import *
from fastcore.xtras import *

import ast,functools
from tinykernel import TinyKernel
from execnb.nbio import read_nb,NbCell
from pprint import pformat,pprint

# %% ../nbs/01_read.ipynb 7
def mk_cell(text, code=True):
    "Create a `NbCell` containing `text`"
    return NbCell(0, dict(cell_type='code' if code else 'markdown', metadata={}, source=text))

# %% ../nbs/01_read.ipynb 8
def create_output(txt, mime):
    "Add a cell output containing `txt` of the `mime` text MIME sub-type"
    return [{"data": { f"text/{mime}": str(txt).splitlines(True) },
             "execution_count": 1, "metadata": {}, "output_type": "execute_result"}]

# %% ../nbs/01_read.ipynb 9
class NBRunner(TinyKernel):
    "A `TinyKernel` subclass that adds a `run` method to execute notebook cells"
    def run(self, cell):
        res = self(cell.source)
        if not res: return
        if hasattr(res, '_repr_html_'): mime,res = 'html',res._repr_html_()
        elif hasattr(res, '_repr_markdown_'): mime,res = 'markdown',res._repr_markdown_()
        else: mime,res = 'plain',str(res)
        cell.outputs = create_output(res, mime)

    def exec_nb(self, nb):
        "`run` all cells in `nb`"
        for cell in nb.cells: self.run(cell)

# %% ../nbs/01_read.ipynb 14
@call_parse
def nbprocess_create_config(
    user:str, # Repo username
    lib_name:str=None, # Name of library
    description='TODO fill me in', # Description for pypi
    author='TODO fill me in', # Author for pypi
    author_email='todo@example.org', # Email for pypi
    path:str='.', # Path to create config file
    cfg_name:str='settings.ini', # Name of config file to create
    branch:str='master', # Repo branch
    host:str='github', # Repo hostname
    git_url:str="https://github.com/%(user)s/%(lib_name)s/tree/%(branch)s/", # Repo URL
    custom_sidebar:bool_arg=False, # Create custom sidebar?
    nbs_path:str='.', # Name of folder containing notebooks
    lib_path:str='%(lib_name)s', # Folder name of root module
    doc_path:str='docs', # Folder name containing docs
    tst_flags:str='', # Test flags
    version:str='0.0.1', # Version number
    keywords='python', # Keywords for pypi
    license='apache2', # License for pypi
    copyright='', # Copyright for pypi, defaults to author from current year
    status='3', # Status for pypi
    min_python='3.6', # Minimum python version for pypi
    audience='Developers', # Audience for pypi
    language='English' # Language for pypi
):
    "Creates a new config file for `lib_name` and `user` and saves it."
    if lib_name is None:
        parent = Path.cwd().parent
        lib_name = parent.parent.name if parent.name=='nbs' else parent.name
    if not copyright: copyright = f'{datetime.now().year} ownwards, {author}'
    g = locals()
    config = {o:g[o] for o in 'host lib_name user branch nbs_path doc_path \
        description author author_email keywords license tst_flags version custom_sidebar \
        copyright status min_python audience language git_url lib_path'.split()}
    save_config_file(Path(path)/cfg_name, config)

# %% ../nbs/01_read.ipynb 16
@functools.lru_cache(maxsize=None)
def get_config(cfg_name='settings.ini', path=None):
    "`Config` for ini file found in `path` (defaults to `cwd`)"
    cfg_path = Path.cwd() if path is None else Path(path)
    while cfg_path != cfg_path.parent and not (cfg_path/cfg_name).exists(): cfg_path = cfg_path.parent
    return Config(cfg_path, cfg_name=cfg_name)

# %% ../nbs/01_read.ipynb 19
def config_key(c, default=None, path=True, missing_ok=False):
    "Look for key `c` in settings.ini and fail gracefully if not found and no default provided"
    try: cfg = get_config()
    except FileNotFoundError:
        if missing_ok and default is not None: return default
        else: raise ValueError('settings.ini not found')
    res = cfg.path(c) if path else cfg.get(c, default=default)
    if res is None: raise ValueError(f'`{c}` not specified in settings.ini')
    return res

# %% ../nbs/01_read.ipynb 21
_init = '__init__.py'

def _has_py(fs): return any(1 for f in fs if f.endswith('.py'))

def add_init(path):
    "Add `__init__.py` in all subdirs of `path` containing python files if it's not there already"
    # we add the lowest-level `__init__.py` files first, which ensures _has_py succeeds for parent modules
    path = Path(path)
    path.mkdir(exist_ok=True)
    if not (path/_init).exists(): (path/_init).touch()
    for r,ds,fs in os.walk(path, topdown=False):
        r = Path(r)
        subds = (os.listdir(r/d) for d in ds)
        if _has_py(fs) or any(filter(_has_py, subds)) and not (r/_init).exists(): (r/_init).touch()

# %% ../nbs/01_read.ipynb 25
def write_cells(cells, hdr, file, offset=0):
    "Write `cells` to `file` along with header `hdr` starting at index `offset` (mainly for nbprocess internal use)"
    for cell in cells:
        if cell.source.strip(): file.write(f'\n\n{hdr} {cell.idx_+offset}\n{cell.source}')

# %% ../nbs/01_read.ipynb 26
def basic_export_nb(fname, name, dest=None):
    "Basic exporter to bootstrap nbprocess"
    if dest is None: dest = config_key('lib_path')
    fname,dest = Path(fname),Path(dest)
    nb = read_nb(fname)

    # grab the source from all the cells that have an `export` comment
    cells = L(cell for cell in nb.cells if re.match(r'#\s*\|export', cell.source))

    # find all the exported functions, to create `__all__`:
    trees = cells.map(NbCell.parsed_).concat()
    funcs = trees.filter(risinstance((ast.FunctionDef,ast.ClassDef))).attrgot('name')
    exp_funcs = [f for f in funcs if f[0]!='_']

    # write out the file
    with (dest/name).open('w') as f:
        f.write(f"# %% auto 0\n__all__ = {exp_funcs}")
        write_cells(cells, f"# %% {fname.relpath(dest)}", f)
        f.write('\n')
