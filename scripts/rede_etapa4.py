#!/usr/bin/env python3
"""
rede_etapa4.py — quarta rodada da Rede de empresas (13/11/2026, comentários do autor). Roda depois de rede_etapa3.py.

  GE × TZ        os casos ganham um resumo da cidade e do histórico, tirado das fichas do Apêndice H (r103)
  A rede         filtro no topo (por grupo ou por cidade), que acende na rede os grupos com endereço na cidade;
                 linhas com peso visível; lista de municípios menor
  Concentração   a escala de confiança fica fixa no topo e quantificada; "A rede em números" vem para cá,
                 em barras; a lista dos 327 grupos ganha as colunas de linhagem (C) e federação (D)
  Além do ônibus grupos por federação em botões visíveis; holdings em etiquetas e setores em barras;
                 sai "Onde os grupos se encontram fora do ônibus"
  Pé da página   sai o "Sobre os dados, o método e os limites"; fica uma linha com a ressalva de pessoas físicas
"""
import os, re, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARQ = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, 'rede-ge-proposta.html')
PAINEL = sys.argv[2] if len(sys.argv) > 2 else 'painel.html'
s = open(ARQ, encoding='utf-8').read()
assert 'rede_etapa3' in s and 'rede_etapa4' not in s, 'rode rede_etapa3.py antes, uma vez só'

def troca(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, f'âncora com {c} ocorrência(s), esperado {n}: {a[:100]!r}'
    s = s.replace(a, b)
def bloco(ini, tag='details'):
    """corta o elemento que começa em `ini` (equilibrando a tag) e devolve o texto"""
    global s
    i = s.index(ini); prof, k = 0, i
    while True:
        a = s.find('<' + tag, k); f = s.find('</' + tag + '>', k)
        if a != -1 and a < f: prof += 1; k = a + len(tag) + 1
        else:
            prof -= 1; k = f + len(tag) + 3
            if prof == 0: break
    t = s[i:k]; s = s[:i] + s[k:]; return t

# ------------------------------------------------------------------ GE × TZ: os casos, com a cidade e o histórico (fichas do Apêndice H, r103)
CASOS = {
 '3301900': ('Itaboraí (RJ)', '224 mil habitantes · franja do arranjo do Rio de Janeiro · universal desde 2025',
   [('nov/2023', 'O Executivo decide a gratuidade sem negociar com a concessionária.'),
    ('dez/2023 a jul/2024', 'Uma liminar suspende o serviço.'),
    ('mai/2025', 'A gratuidade vira universal: "ninguém mais paga passagem". Entra por aditivo à concessão da Maravilha Auto Ônibus, que opera desde 1985.'),
    ('hoje', 'A lei só autoriza o subsídio ao operador; a gratuidade está no aditivo. A empresa alega não receber, e a dívida é contestada.')],
   'A lei amarrou o subsídio à concessão vigente: a gratuidade cabe no contrato que já existia. O operador é empresa familiar local, sem relação com grupos da rede.', None),
 '3302700': ('Maricá (RJ)', '197 mil habitantes · franja do arranjo do Rio de Janeiro · universal desde 2014',
   [('2013', 'A gratuidade cobre parte das linhas, em concorrência com as concessionárias privadas.'),
    ('dez/2014', 'A Empresa Pública de Transportes (EPT) assume e a gratuidade vira universal, paga sobretudo pelos royalties do petróleo. As concessionárias contestam na Justiça.'),
    ('2024 e 2025', 'A EPT passa a alugar ônibus com motorista, pagos por quilômetro. Hoje, 132 dos 157 ônibus da frota gratuita são de empresas contratadas.'),
    ('2025', 'Uma empresa do maior grupo do país volta como locadora, pelo maior contrato anual de Tarifa Zero do levantamento.')],
   'A cidade rompeu com a concessão, e o incumbente de grande grupo voltou por outro contrato.', 'GE-001'),
 '3548807': ('São Caetano do Sul (SP)', '166 mil habitantes · franja do arranjo de São Paulo · universal desde 2023',
   [('out/2023', 'Tarifa Zero universal por aditivo à concessão da Vipe.'),
    ('2024 a 2026', 'A demanda passa de 20 mil para 80 mil passageiros por dia, contra 50% de aumento previsto.'),
    ('14/07/2026', 'Um aditivo troca a remuneração por quilômetro pelo custo apurado menos as receitas.'),
    ('15/07/2026', 'Um dia depois, a gratuidade passa a ser só de moradores cadastrados; quem vem de fora volta a pagar R$ 5.')],
   'O recuo veio com o mesmo operador, e o contrato foi refeito antes da norma.', None),
 '3531803': ('Monte Mor (SP)', '65 mil habitantes · franja do arranjo de Campinas · universal de 2023 a 2025',
   [('29/12/2023', 'Tarifa Zero universal, por aditivo à concessão da Rápido Luxo.'),
    ('09/09/2025', 'A Câmara aprova por 13 a 2 a lei que revoga a gratuidade universal.'),
    ('30/10/2025', 'A "Tarifa do Bem" passa a dar gratuidade só a idosos, pessoas com deficiência e famílias do CadÚnico em extrema pobreza.'),
    ('01/11/2025', 'Os demais voltam a pagar. O recuo é atribuído à restrição orçamentária.')],
   'A gratuidade universal virou focalizada sem trocar a concessão.', None),
}
def caso_rico(cod, rotulo_extra=''):
    nome, linha, hist, leitura, ge = CASOS[cod]
    h = ''.join(f'<li><b>{d}</b> {t}</li>' for d, t in hist)
    ge_lk = f'<a href="#GE-001" class="lk-rede" data-ge="{ge}">ver o grupo na rede →</a>' if ge else ''
    return (f'<div class="caso-rico"><div class="cr-cab"><b>{nome}</b><span>{linha}</span></div><ol class="cr-hist">{h}</ol>'
            f'<p class="cr-leit">{leitura}</p><div class="cr-lk"><a href="{PAINEL}#mun-{cod}">ver no painel →</a>{ge_lk}</div></div>')
# caixa 4: Monte Mor e São Caetano, ricos
i = s.index('<div class="casos"><a class="caso" href="' + PAINEL + '#mun-3531803">')
j = s.index('</div>', s.index('#mun-3548807', i)) + len('</div>')
s = s[:i] + '<div class="casos-ricos">' + caso_rico('3531803') + caso_rico('3548807') + '</div>' + s[j:]
# "Os casos": os quatro, ricos
i = s.index('<div class="panel" id="ge-casos"')
j = s.index('</div></div>\n', i) + len('</div></div>\n')
s = s[:i] + ('<div class="panel" id="ge-casos" style="margin-top:16px;"><h2>Os casos: o contrato condiciona a política</h2>'
             '<p class="legenda">As trajetórias que a tese documenta caso a caso (Seções 7.3 a 7.5 e 8.4), resumidas das fichas do Apêndice H.</p>'
             '<div class="casos-ricos">' + ''.join(caso_rico(c) for c in ('3301900', '3302700', '3548807', '3531803')) + '</div></div>\n') + s[j:]

# ------------------------------------------------------------------ pé da página: sai o "Sobre…", fica uma linha
bloco('<details class="rodape-sobre" id="sobre">')
i = s.index('  <aside class="cta-dados"')
s = s[:i] + ('  <p class="nota-pf">Nenhum nome de pessoa física como sócio é publicado: o nome de mercado de alguns grupos é o do fundador e aparece como marca. '
             'Grupo econômico aqui é uma inferência a partir dos sócios em comum no cadastro da Receita Federal; endereço não é operação. O método e os limites estão no Capítulo 6 e no Apêndice E da tese.</p>\n') + s[i:]

# ------------------------------------------------------------------ A rede: filtro no topo (grupo ou cidade)
achar = re.search(r'\s*<label class="busca">Achar grupo <input id="redeBusca".*?</label>', s, re.S).group(0)
s = s.replace(achar, '', 1)
muni_in = re.search(r'\s*<input id="muniBusca" list="muniBuscaList"[^>]*>\s*<datalist id="muniBuscaList"></datalist>', s, re.S).group(0)
s = s.replace(muni_in, '', 1)
muni_res = bloco('<div id="muniGrupos">', 'div')
troca('<h3 style="margin:4px 0 8px;font-size:13px;">Que grupos têm endereço num município</h3>', '')
FILTRO = ('  <div class="filtro-rede"><span class="fr-t">Filtrar a rede</span>'
          '<label>por grupo <input id="redeBusca" list="redeBuscaList" placeholder="nome ou nome de mercado…" autocomplete="off" spellcheck="false"><datalist id="redeBuscaList"></datalist></label>'
          '<label>por cidade <input id="muniBusca" list="muniBuscaList" placeholder="digite o nome do município…" autocomplete="off" spellcheck="false"><datalist id="muniBuscaList"></datalist></label>'
          '<button type="button" class="bt2" id="limpaFiltro">Limpar</button>'
          + muni_res.replace('<div id="muniGrupos">', '<div id="muniGrupos" class="fr-res">') + '</div>\n')
troca('  <div class="grid rede-grid">', FILTRO + '  <div class="grid rede-grid">')
# "Onde os grupos estão": só o alcance territorial
troca('<h2>Onde os grupos estão</h2><p>Os grupos de maior alcance e os que têm endereço em cada município. Endereço não é operação.</p>',
      '<h2>Os grupos de maior alcance</h2><p>Em quantos municípios cada grupo tem endereço. Para ver os grupos de uma cidade, use o filtro no topo da rede.</p>')

# ------------------------------------------------------------------ Concentração: escala fixa e quantificada; rede em números; colunas C e D
MED = bloco('<details class="pacote" id="medidas-cx">')
MED = MED.replace('<span class="pnum">2</span>', '<span class="pnum">2</span>')
troca('<details class="pacote" id="lista-grupos"><summary class="phead"><span class="pnum">2</span>',
      '<details class="pacote" id="lista-grupos"><summary class="phead"><span class="pnum">3</span>')
i = s.index('<details class="pacote" id="lista-grupos">'); i = s.rindex('\n', 0, i) + 1
s = s[:i] + MED.strip() + '\n' + s[i:]
troca('<div class="paneintro"><p class="resposta-rede">Poucos donos, muito capital:',
      '<div class="panel escala-fixa"><h2>A escala de confiança: de grupo a federação</h2><p class="legenda">Como a tese junta os 327 grupos econômicos, do vínculo mais forte ao mais fraco, e quanto cada passo muda a concentração. A leitura principal é a das unidades de controle (A + B).</p><div id="escalaFixa"></div></div>\n  <div class="paneintro" hidden><p class="resposta-rede">Poucos donos, muito capital:')
troca('<div id="geEscala" class="getabwrap" style="max-height:none;"></div>', '<div id="geEscala" class="getabwrap" style="max-height:none;" hidden></div>')
troca('<th data-k="ub">Unidade</th>', '<th data-k="ub">Unidade (A/B)</th><th>Linhagem (C)</th><th>Federação (D)</th>')

# ------------------------------------------------------------------ Além do ônibus: grupos por federação, visíveis; sai "Onde os grupos se encontram"
troca('<label>Federação e grupo <select id="patFed"><option value="">escolha…</option></select></label>', '')
troca('<div id="patVerRede" style="margin:-4px 0 8px;"></div>',
      '<div id="patFedChips" class="fedchips"></div>\n    <div id="patVerRede" style="margin:4px 0 8px;"></div>')
troca('<details class="pacote" id="alem-encontros">', '<details class="pacote" id="alem-encontros" hidden>')

# ------------------------------------------------------------------ CSS
troca('</style>\n</head>', '''  /* ===== rede_etapa4 (13/11/2026) ===== */
  .casos-ricos{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px;margin:6px 0 0;}
  .caso-rico{background:var(--panel2);border:1px solid var(--border);border-radius:10px;padding:14px 16px;display:flex;flex-direction:column;gap:8px;}
  .cr-cab b{display:block;font-size:16px;} .cr-cab span{font-size:12px;color:var(--muted);}
  ol.cr-hist{list-style:none;margin:0;padding:0 0 0 12px;border-left:2px solid var(--rosa);display:grid;gap:7px;font-size:12.5px;line-height:1.5;}
  ol.cr-hist li b{display:block;font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--amarelo);}
  .cr-leit{margin:2px 0 0;font-size:13px;font-weight:700;color:var(--text);}
  .cr-lk{display:flex;gap:14px;margin-top:auto;font-size:12px;} .cr-lk a{color:var(--rosa) !important;}
  .nota-pf{font-size:11.5px;color:var(--muted);margin:22px 0 0;line-height:1.5;max-width:960px;}
  .filtro-rede{display:flex;flex-wrap:wrap;align-items:center;gap:10px 16px;background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:12px 16px;margin:0 0 14px;}
  .filtro-rede .fr-t{font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.06em;color:var(--amarelo);}
  .filtro-rede label{display:flex;align-items:center;gap:8px;font-size:12.5px;color:var(--muted);}
  .filtro-rede input{background:var(--panel2);border:2px solid var(--border);border-radius:8px;color:var(--text);font:inherit;font-size:13.5px;padding:7px 10px;width:250px;}
  .filtro-rede input:focus{border-color:var(--amarelo);outline:none;}
  .filtro-rede .bt2{margin:0;font-size:12px;padding:7px 11px;}
  .fr-res{flex:1 1 100%;font-size:12.5px;} .fr-res:empty{display:none;}
  .fr-res ul{display:flex;flex-wrap:wrap;gap:6px;list-style:none;margin:6px 0;padding:0;} .fr-res li{background:var(--panel2);border:1px solid var(--border);border-radius:14px;padding:3px 10px;}
  .fr-res li span{display:none;} .fr-res a{color:var(--text) !important;} .fr-res p a{color:var(--rosa) !important;}
  @media (max-width:640px){ .filtro-rede input{width:100%;} .filtro-rede label{flex:1 1 100%;} }
  #fichaPanel details.fichapol > summary{font-size:12.5px !important;font-weight:600;}
  .escala-fixa table{width:100%;border-collapse:collapse;font-size:13px;}
  .escala-fixa td,.escala-fixa th{padding:9px 8px;border-bottom:1px solid var(--border);text-align:left;vertical-align:middle;}
  .escala-fixa th{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);}
  .escala-fixa td.q b{font-size:20px;color:var(--amarelo);} .escala-fixa td.q span{display:block;font-size:11.5px;color:var(--muted);}
  .escala-fixa .ef{display:flex;align-items:center;gap:8px;} .escala-fixa .ef i{display:block;height:10px;background:var(--rosa);border-radius:3px;}
  .escala-fixa tr.teto td{opacity:.75;}
  .medbars{display:grid;grid-template-columns:1fr 1fr;gap:20px;} @media (max-width:820px){ .medbars{grid-template-columns:1fr;} }
  .mb-lin{display:grid;grid-template-columns:minmax(0,1fr) 120px 34px;gap:8px;align-items:center;font-size:12.5px;margin:4px 0;}
  .mb-lin a{color:var(--text) !important;text-decoration:none;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;} .mb-lin a:hover{color:var(--amarelo) !important;}
  .mb-bar{height:10px;background:var(--panel2);border-radius:3px;overflow:hidden;} .mb-bar i{display:block;height:100%;background:var(--amarelo);}
  .mb-v{text-align:right;color:var(--muted);}
  .fedchips{display:grid;gap:8px;margin:6px 0 10px;}
  .fc-lin{display:grid;grid-template-columns:72px 1fr;gap:8px;align-items:start;}
  .fc-lin > b{font-size:11px;color:var(--muted);padding-top:6px;}
  .fc-lin button{background:var(--panel2);border:1px solid var(--border);border-radius:14px;color:var(--text);font:inherit;font-size:12px;padding:4px 10px;margin:0 6px 6px 0;cursor:pointer;}
  .fc-lin button:hover{border-color:var(--amarelo);} .fc-lin button.on{background:var(--amarelo);border-color:var(--amarelo);color:#0E0E10;font-weight:700;}
  #patLista .hchips{display:flex;flex-wrap:wrap;gap:5px;margin:6px 0 2px;} #patLista .hchips span{background:rgba(255,45,107,.12);border:1px solid rgba(255,45,107,.5);border-radius:12px;padding:2px 8px;font-size:11.5px;}
  #patLista details.setor{margin:4px 0;} #patLista details.setor > summary{list-style:none;cursor:pointer;display:grid;grid-template-columns:minmax(0,1fr) 110px 30px;gap:8px;align-items:center;font-size:12.5px;}
  #patLista details.setor > summary::-webkit-details-marker{display:none;}
  #patLista details.setor .sb{height:10px;background:var(--panel2);border-radius:3px;overflow:hidden;} #patLista details.setor .sb i{display:block;height:100%;}
  #patLista details.setor ul{margin:4px 0 8px;padding-left:18px;font-size:12px;}
</style>
</head>''')

# ------------------------------------------------------------------ JS
s = s.replace('<meta name="proposta" content="rede_etapa3">\n</body>', r'''<script>
// rede_etapa4
// linhas com peso visível: espessura proporcional aos sócios em comum
LIN_EL.forEach(l => { l._w = l._e.w; });
const _des0 = desenha;
let FOCO_MUN = null, ULT_MUN = null;
desenha = function () {
  _des0();
  const k = R.k;
  const foco = selecionado ? null : FOCO_MUN;
  for (const l of LIN_EL) {
    if (l.style.display === 'none') continue;
    const e = l._e;
    l.setAttribute('stroke-width', ((e.t === 'fusao' ? 2 : .4) + Math.sqrt(e.w) * .6) / Math.pow(k, .85));
    if (foco) l.setAttribute('stroke-opacity', foco.has(e.a) && foco.has(e.b) ? .95 : .05);
  }
  if (foco) for (const s0 of SIM) {
    const c = NO_EL.get(s0.id), t = TX_EL.get(s0.id); if (!c || c.style.display === 'none') continue;
    const on = foco.has(s0.id); c.setAttribute('fill-opacity', on ? .95 : .12);
    if (on) { t.style.display = ''; const r = raio(s0.n); t.setAttribute('x', s0.x + r + 3 / k); t.setAttribute('y', s0.y + 3.5 / k); t.setAttribute('font-size', 11 / k); }
    else t.style.display = 'none';
  }
};
// legenda: o que a espessura quer dizer
(() => { const lg = document.getElementById('redeLeg'); if (lg && !lg.querySelector('.esp')) lg.insertAdjacentHTML('beforeend', '<span class="esp" style="margin-left:10px;">espessura da linha: quantos sócios os dois grupos têm em comum</span>'); })();
// filtro por cidade: acende na rede os grupos com endereço no município
function focoMuni() {
  const cod = ROT2COD.get(busca.value.trim());
  if (!cod) { if (!busca.value.trim() && FOCO_MUN) { FOCO_MUN = null; ULT_MUN = null; document.getElementById('muniGrupos').innerHTML = ''; desenha(); } return; }
  if (cod === ULT_MUN) return; ULT_MUN = cod;
  const ids = (ARS.presenca[cod] || []).filter(id => NOS.has(id));
  FOCO_MUN = new Set(ids); if (selecionado) seleciona(null);
  if (document.getElementById('tab-controle').hidden) abreAba('controle');
  const vis = ids.filter(id => { const s0 = SIMI.get(id); return s0 && visivel(s0); });
  if (vis.length) enquadra(vis); else desenha();
}
busca.addEventListener('input', focoMuni); busca.addEventListener('change', focoMuni);
document.getElementById('limpaFiltro')?.addEventListener('click', () => {
  FOCO_MUN = null; ULT_MUN = null; busca.value = ''; const rb = document.getElementById('redeBusca'); if (rb) rb.value = '';
  document.getElementById('muniGrupos').innerHTML = ''; seleciona(null); enquadra(null);
});
document.getElementById('muniGrupos').innerHTML = '';
// ao selecionar um grupo, o filtro da cidade sai de cena
const _sel1 = seleciona;
seleciona = function (id, rolar, modo) { if (id) { FOCO_MUN = null; ULT_MUN = null; } _sel1(id, rolar, modo); };

// Concentração: a escala de confiança, quantificada
(() => {
  const el = document.getElementById('escalaFixa'); if (!el) return;
  const multi = ARS.unidades.filter(u => u.membros.length > 1);
  const qA = multi.filter(u => u.grau === 'A'), qB = multi.filter(u => u.grau !== 'A');
  const gA = qA.reduce((t, u) => t + u.membros.length, 0), gB = qB.reduce((t, u) => t + u.membros.length, 0);
  const gC = ARS.linhagens.reduce((t, l) => t + l.membros.length, 0);
  const uD = ARS.federacoes.reduce((t, f) => t + f.unidades.length, 0);
  const F = Object.fromEntries(ARS.funil.map(f => [f.grau, f]));
  const maxM = Math.max(...ARS.funil.map(f => f.meia));
  const efeito = f => f ? `<div class="ef"><i style="width:${(120 * f.meia / maxM).toFixed(0)}px"></i><span><b>${f.meia}</b> detêm metade do capital <span style="color:var(--muted);">(de ${f.n})</span></span></div>` : '';
  const E = Object.fromEntries(ARS.escala.map(e => [e.grau, e]));
  const lin = (g, q, qs, ef, teto) => `<tr${teto ? ' class="teto"' : ''}><td><span class="grau g${g}">${g}</span></td><td><b>${esc(E[g]?.nome || '')}</b></td><td class="q" title="${esc(E[g]?.regra || '')}"><b>${q}</b><span>${qs}</span></td><td>${ef}</td></tr>`;
  el.innerHTML = `<table><thead><tr><th>Grau</th><th>O que junta</th><th>Quantos</th><th>Quantas unidades detêm metade do capital</th></tr></thead><tbody>
    <tr><td>—</td><td><b>Grupos da rede (códigos GE)</b></td><td class="q"><b>${ARS.nos.length}</b><span>grupos</span></td><td>${efeito(F['—'])}</td></tr>
    ${lin('A', qA.length, `unidades, juntando ${gA} grupos`, '<span style="font-size:11.5px;color:var(--muted);">somadas às de B na linha seguinte</span>', false)}
    ${lin('B', qB.length, `unidades, juntando ${gB} grupos`, efeito(F['A+B']), false)}
    ${lin('C', ARS.linhagens.length, `linhagens familiares, com ${gC} grupos`, efeito(F['+C']), false)}
    ${lin('D', ARS.federacoes.length, `federações, com ${uD} unidades`, efeito(F['+D']) + '<span style="font-size:11px;color:var(--muted);">só teto: articulação, e não controle</span>', true)}
  </tbody></table>`;
})();
// Concentração: a rede em números, em barras
renderMedidas = function () {
  const box = document.getElementById('redeMedidas'); if (!box) return;
  const N = ARS.nos.length, E = ARS.arestas.length, lig = ARS.nos.filter(n => ADJ.get(n.id).size).length;
  const topGrau = [...ARS.nos].sort((a, b) => ADJ.get(b.id).size - ADJ.get(a.id).size).slice(0, 10);
  const topBet = rankBet.slice(0, 10);
  const barras = (lista, val) => { const mx = Math.max(...lista.map(val)) || 1;
    return lista.map(n => `<div class="mb-lin"><a href="#" class="gelink" data-id="${n.id}">${esc(nomeG(n))}</a><div class="mb-bar"><i style="width:${(100 * val(n) / mx).toFixed(0)}%"></i></div><div class="mb-v">${Math.round(val(n))}</div></div>`).join(''); };
  box.innerHTML = `<p class="resposta-rede" style="font-size:14px;">Dos ${fmt(N)} grupos, <b>${fmt(lig)}</b> têm ligação com outro grupo, em ${ORD_COMP.length} conjuntos separados; o maior reúne ${TAM_COMP.get(ORD_COMP[0])} grupos. São ${fmt(E)} ligações: em média, ${(2 * E / N).toFixed(1).replace('.', ',')} por grupo.</p>
    <div class="medbars"><div><h3 style="font-size:13px;margin:0 0 4px;">Os mais conectados</h3><p class="legenda">Com quantos grupos se ligam.</p>${barras(topGrau, n => ADJ.get(n.id).size)}</div>
    <div><h3 style="font-size:13px;margin:0 0 4px;">Os que fazem a ponte</h3><p class="legenda">Quantas vezes estão no caminho mais curto entre outros dois grupos.</p>${barras(topBet, n => BETW.get(n.id))}</div></div>
    <p class="legenda" style="margin-top:10px;">Ligação por sócio em comum é vínculo fraco: leia como posição na rede de sócios, e não como poder de controle.</p>`;
};
renderMedidas();
// lista dos 327: colunas de linhagem (C) e federação (D)
const _tab0 = renderTabela;
renderTabela = function () {
  _tab0();
  document.querySelectorAll('#geTable tbody tr').forEach(tr => {
    const n = NOS.get(tr.dataset.id), u = n && UNI.get(n.ub); if (!n) return;
    const tds = tr.querySelectorAll('td'); const ref = tds[3]; if (!ref || tr.dataset.cd) return;
    const lin = u?.lin && LIN.get(u.lin), fed = u?.fed;
    ref.insertAdjacentHTML('afterend', `<td>${lin ? `<span class="grau gC">C</span> ${esc(lin.nome)}` : '—'}</td><td>${fed ? `<span class="grau gD">D</span> ${fed}` : '—'}</td>`);
    tr.dataset.cd = '1';
  });
};
renderTabela();

// Além do ônibus: os grupos por federação, em botões
(() => {
  const box = document.getElementById('patFedChips'); if (!box || !window.PAT) return;
  const linhas = ARS.federacoes.map(f => {
    const gs = f.unidades.flatMap(u => (UNI.get(u)?.membros || [])).filter(g => NOS.has(g) && window.PAT.tem(g));
    return gs.length ? `<div class="fc-lin"><b>${f.id}</b><div>${gs.map(g => `<button type="button" data-g="${g}">${esc(nomeG(NOS.get(g)))}</button>`).join('')}</div></div>` : '';
  }).join('');
  box.innerHTML = `<p class="legenda" style="margin:0 0 4px;">Escolha um grupo. Eles estão organizados pelas federações a que pertencem (grau D da escala de confiança).</p>${linhas}`;
  box.addEventListener('click', e => { const b = e.target.closest('button[data-g]'); if (!b) return;
    box.querySelectorAll('button.on').forEach(x => x.classList.remove('on')); b.classList.add('on'); window.PAT.mostra(b.dataset.g); });
})();
// Além do ônibus: holdings em etiquetas, setores em barras
(() => {
  const el = document.getElementById('patLista'); if (!el) return;
  const arruma = () => {
    if (el.dataset.ok === el.innerHTML.length + '') return;
    const h4s = [...el.querySelectorAll(':scope > h4')]; if (!h4s.length) return;
    const total = h4s.slice(1).reduce((t, h) => t + (parseInt((h.textContent.match(/\((\d+)\)\s*$/) || [0, 0])[1]) || 0), 0) || 1;
    const novo = document.createElement('div'); let hold = '';
    h4s.forEach((h, i) => {
      const ul = h.nextElementSibling && h.nextElementSibling.matches('ul') ? h.nextElementSibling : null;
      if (i === 0) {
        const nomes = ul ? [...ul.querySelectorAll('li')].map(li => (li.firstChild?.textContent || li.textContent).trim()) : [];
        hold = `<details class="hold" style="margin-top:12px;"><summary style="cursor:pointer;font-weight:700;font-size:13px;">${h.textContent} <span style="font-weight:400;color:var(--muted);">: ver os nomes</span></summary><div class="hchips">${nomes.map(n => `<span>${n}</span>`).join('')}</div></details>`;
        novo.insertAdjacentHTML('beforeend', `<h4 style="margin:0 0 2px;">Empresas de outros setores, por setor</h4><p class="legenda" style="margin:0 0 6px;">Clique num setor para ver as empresas.</p>`);
      } else {
        const n = parseInt((h.textContent.match(/\((\d+)\)\s*$/) || [0, 0])[1]) || 0;
        const cor = h.querySelector('i')?.style.background || 'var(--amarelo)';
        const nome = h.textContent.replace(/\s*\(\d+\)\s*$/, '');
        const d = document.createElement('details'); d.className = 'setor';
        d.innerHTML = `<summary><span>${nome}</span><span class="sb"><i style="width:${(100 * n / Math.max(...h4s.slice(1).map(x => parseInt((x.textContent.match(/\((\d+)\)\s*$/) || [0, 0])[1]) || 0))).toFixed(0)}%;background:${cor};"></i></span><span style="text-align:right;color:var(--muted);">${n}</span></summary>`;
        if (ul) d.appendChild(ul.cloneNode(true));
        novo.appendChild(d);
      }
    });
    if (hold) novo.insertAdjacentHTML('beforeend', hold);
    [...el.querySelectorAll(':scope > p')].forEach(p => novo.appendChild(p.cloneNode(true)));
    el.innerHTML = ''; el.appendChild(novo); el.dataset.ok = el.innerHTML.length + '';
  };
  new MutationObserver(arruma).observe(el, { childList: true });
  arruma();
  const vr = document.getElementById('patVerRede');
  new MutationObserver(() => { const a = vr.querySelector('a'); if (a && !a.dataset.ok) { a.dataset.ok = 1; a.textContent = 'ver este grupo na aba A rede →'; } }).observe(vr, { childList: true });
})();
// GE × TZ: "ver o grupo na rede"
document.addEventListener('click', e => { const a = e.target.closest('.lk-rede'); if (!a) return; e.preventDefault(); abreAba('controle'); seleciona(a.dataset.ge, true); });
</script>
<meta name="proposta" content="rede_etapa4">
</body>''', 1)
assert 'rede_etapa4' in s
open(ARQ, 'w', encoding='utf-8').write(s)
print('etapa 4 da rede aplicada:', ARQ, len(s.encode()), 'bytes')
