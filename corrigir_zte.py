#!/usr/bin/env python3
"""Gera variante local com verificações separadas de conta normal e admin.
Não contacta o router. Não inclui credenciais no repositório.
"""
from pathlib import Path
import re
import subprocess
import sys

base = Path.home() / "digi-f8748" / "DIGI-F8748-linux"
src = base / "digi-f8748.sh"
test_src = base / "digi-f8748-teste.sh"
if not src.is_file() or not test_src.is_file():
    sys.exit("Faltam ficheiros locais do projeto; nenhuma alteração feita.")
original = src.read_text()
if "cmd_verify >/dev/null" not in original or "cmd_verify(){" not in original:
    sys.exit("Formato inesperado do original; nenhuma alteração feita.")
original = original.replace("  cmd_verify >/dev/null\n", "  cmd_verify normal >/dev/null\n", 1)
original = original.replace("cmd_verify(){\n", 'cmd_verify(){\n  ROLE="${1:-admin}"\n', 1)
old = '''  if curl -s -m 15 -A Mozilla/5.0 -b "$CJ" "http://$HOST/" | grep -q 'curRight = "1"'; then
    log "[+] login admin web confirmado (curRight=1)"
  else
    die "login web rechazado o no confirmado (comprueba --web-user y --web-pass)"
  fi'''
new = '''  PAGE=$(curl -fsS -m 15 -A Mozilla/5.0 -b "$CJ" "http://$HOST/") || die "no se pudo consultar estado web"
  STATUS=$(printf '%s' "$PAGE" | python3 -c '
import codecs,re,sys
page=sys.stdin.read()
r=re.search(r"var\\s+curRight\\s*=\\s*\\\"([^\\\"]+)\\\"",page)
m=re.search(r"var\\s+NowLoginStatus\\s*=\\s*\\\"([^\\\"]+)\\\"",page)
rights=r.group(1) if r else "unknown"
state=codecs.decode(m.group(1),"unicode_escape") if m else "unknown"
print(rights+" "+state)
') || die "no se pudo analizar estado web"
  if [ "$ROLE" = "normal" ]; then
    [ "$STATUS" = "2 showCommonPage" ] || die "login normal no confirmado (estado=$STATUS)"
    log "[+] login normal confirmado"
  else
    [ "$STATUS" = "1 showCommonPage" ] || die "login admin no confirmado (estado=$STATUS)"
    log "[+] login admin confirmado"
  fi'''
if original.count(old) != 1:
    sys.exit("Bloco de validação original não encontrado; nenhuma alteração feita.")
original = original.replace(old,new,1)
original = original.replace("grep -q 'loginErrMsg\":\"[^\"]*.'", "grep -qE '\"loginErrMsg\":\"[^\"]+\"'")
test = test_src.read_text()
m = re.search(r'^\s*VPASS="([^"\\]*)"\s*$',test,re.M)
if not m:
    sys.exit("Não encontrei password fixa no diagnóstico; nenhuma alteração feita.")
password=m.group(1)
if len(password)<8 or any(x in password for x in '\n\r`$\\"'):
    sys.exit("Password temporária inválida ou incompatível.")
needle='CMD="${1:-}"; [ $# -gt 0 ] && shift'
if original.count(needle)!=1:
    sys.exit("Parser inesperado; nenhuma alteração feita.")
original=original.replace(needle,needle+'\n# Credencial temporária local; nunca publicar o resultado.\nWEBU="user"; WEBP="'+password+'"',1)
out=base/"digi-f8748-corrigido.sh"
out.write_text(original)
out.chmod(0o700)
result=subprocess.run(["bash","-n",str(out)],capture_output=True,text=True)
if result.returncode:
    out.unlink()
    sys.exit("Erro de sintaxe: "+result.stderr)
print("OK: script gerado e sintaxe Bash válida; não testado no router.")
print("Ficheiro:",out)
