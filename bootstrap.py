"""Populate persistent Docker volume exactly once, never overwrite user data."""
import os,shutil,sqlite3
from pathlib import Path
src=Path(__file__).parent/'data';dst=Path(os.environ.get('DATA_DIR',src));dst.mkdir(parents=True,exist_ok=True)
if src.resolve()!=dst.resolve():
 for name in ['search_links.json','search_url.txt','search_large_url.txt','search_prices_url.txt']+[f'exim-{i}.html' for i in range(6)]:
  if not (dst/name).exists():shutil.copy2(src/name,dst/name)
 if not (dst/'hotels.sqlite').exists():
  with sqlite3.connect(src/'hotels.sqlite') as a,sqlite3.connect(dst/'hotels.sqlite') as b:a.backup(b)
