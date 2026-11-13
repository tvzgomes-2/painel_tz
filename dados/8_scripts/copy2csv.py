#!/usr/bin/env python3
"""Streaming pg_restore (custom dump) -> CSV, one file per table.
Reads a specific schema's data-only dump on stdin (PostgreSQL text COPY format)
and writes <outdir>/<schema>/<table>.csv. No server needed."""
import sys, os, csv, re

OUTDIR = sys.argv[1]
PREFIX = sys.argv[2] if len(sys.argv) > 2 else ""  # só grava schemas com este prefixo
COPY_RE = re.compile(r'^COPY\s+("?[^". ]+"?)\.("?[^". ]+"?)\s*\((.*)\)\s+FROM stdin;')

def unquote(ident):
    ident = ident.strip()
    if ident.startswith('"') and ident.endswith('"'):
        return ident[1:-1].replace('""', '"')
    return ident

def unescape(field):
    if field == r'\N':
        return None
    if '\\' not in field:      # fast path: sem escapes (maioria esmagadora)
        return field
    out, i, n = [], 0, len(field)
    while i < n:
        c = field[i]
        if c == '\\' and i + 1 < n:
            nx = field[i+1]
            out.append({'t':'\t','n':'\n','r':'\r','\\':'\\','b':'\b','f':'\f','v':'\v'}.get(nx, nx))
            i += 2
        else:
            out.append(c); i += 1
    return ''.join(out)

def main():
    writer = None; fh = None; in_copy = False
    tables = 0; rows = 0; cur = None
    for line in sys.stdin:
        line = line.rstrip('\n')
        if not in_copy:
            m = COPY_RE.match(line)
            if m:
                schema, table = unquote(m.group(1)), unquote(m.group(2))
                in_copy = True; cur = f"{schema}.{table}"; rowc = 0
                if PREFIX and not schema.startswith(PREFIX):
                    writer = None; fh = None  # pular este bloco
                    continue
                cols = [unquote(c) for c in m.group(3).split(',')]
                d = os.path.join(OUTDIR, schema)
                os.makedirs(d, exist_ok=True)
                fh = open(os.path.join(d, table + '.csv'), 'w', newline='', encoding='utf-8')
                writer = csv.writer(fh)
                writer.writerow(cols)
                tables += 1
            continue
        if line == r'\.':
            in_copy = False
            if fh: fh.close(); fh = None
            if writer:
                print(f"  {cur}: {rowc} linhas", file=sys.stderr)
                rows += rowc
            writer = None
            continue
        if writer is None:
            continue  # pulando bloco fora do prefixo
        if '\\' not in line:                       # linha sem escapes/nulos: rápido
            writer.writerow(line.split('\t'))
        else:
            writer.writerow([unescape(f) for f in line.split('\t')])
        rowc += 1
    print(f"TOTAL: {tables} tabelas, {rows} linhas", file=sys.stderr)

if __name__ == '__main__':
    main()
