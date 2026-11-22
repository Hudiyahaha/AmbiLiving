import re,sys
s=open('ambiliving-poster.src.html',encoding='utf8').read()
def icon(m):
    name,col=m.group(1),m.group(2)
    svg=open('icons/%s.svg'%name,encoding='utf8').read()
    d=re.search(r'<path d="([^"]+)"',svg).group(1)
    return '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="%s" d="%s"/></svg>'%(col,d)
s=re.sub(r'\{\{ICON:(\w+):(#[0-9A-Fa-f]{6})\}\}',icon,s)
if '--final' in sys.argv: s=re.sub(r"\n<script>var l=.*?</script>","",s,flags=re.S)
open('ambiliving-poster.html','w',encoding='utf8').write(s)
