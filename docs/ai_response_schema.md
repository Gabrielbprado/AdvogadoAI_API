# Esquema de resposta da IA (API -> Front)

## Visão geral
A rota `POST /document/analyze/{doc_id}` retorna um `FinalAnalysisResponse` com quatro blocos principais:
- `extracao` (saída do Leitor)
- `analise` (saída do Analista, agora com campo `avisos`)
- `parecer` (saída do Redator)
- ✨ `jurisprudencia` **(NOVO)** - links automáticos Jusbrasil com termos jurídicos

Campos podem vir vazios (`[]` ou strings ""); use checagem defensiva no front.

## Estrutura detalhada
```jsonc
{
  "extracao": {
    "topicos_principais": ["string"],
    "clausulas": [
      {
        "numero": "string|null",
        "titulo": "string",
        "texto": "string"
      }
    ],
    "pontos_chave": ["string"],
    "informacoes_extraidas": {
      "partes": [ { "tipo": "string|null", "nome": "string", "cnpj": "string|null", "endereco": "string|null" } ],
      "valores": [ { "descricao": "string", "valor": "string|null" } ],
      "datas": [ { "descricao": "string", "data": "string|null", "prazo": "string|null", "valor": "string|null" } ]
    }
  },
  "analise": {
    "riscos": ["string"],
    "inconsistencias": ["string"],
    "clausulas_abusivas": ["string"],
    "melhorias_recomendadas": ["string"],
    "avisos": [
      {"aviso": "string", "detalhe": "string", "trecho": "string|null"}
    ] // resposta explícita aos avisos; detalhe explica ocorrência ou "sem ocorrencias"; trecho aponta referência
  },
  "parecer": {
    "parecer_resumido": "string",
    "parecer_detalhado": "string",
    "contra_proposta": {
      "clausula_vigencia": "string",
      "clausula_multa": "string",
      "clausula_obrigacoes": "string",
      "clausula_resolucao_conflitos": "string"
    }
  },
  "jurisprudencia": [
    {
      "termo": "string",
      "url": "https://www.jusbrasil.com.br/jurisprudencia/busca?q=...",
      "fonte": "Jusbrasil"
    }
  ] // NOVO: array com termos jurídicos identificados automaticamente
}
```

## Exemplo resumido
```json
{
  "extracao": {
    "topicos_principais": ["Objeto", "Preço", "SLA"],
    "clausulas": [
      {"numero": "5", "titulo": "SLA", "texto": "Disponibilidade mínima de 99%."}
    ],
    "pontos_chave": ["Multa de 10% por indisponibilidade"],
    "informacoes_extraidas": {
      "partes": [{"tipo": "contratante", "nome": "Empresa X"}],
      "valores": [{"descricao": "Preço", "valor": "R$ 50.000"}],
      "datas": [{"descricao": "Vigência", "data": "2025-01-01"}]
    }
  },
  "analise": {
    "riscos": ["SLA sem métricas de penalidade graduais"],
    "inconsistencias": [],
    "clausulas_abusivas": ["Multa desproporcional de 20%"],
    "melhorias_recomendadas": ["Definir janela de manutenção"],
    "avisos": [
      {"aviso": "Minutas duplas", "detalhe": "Detectado duplicidade na cláusula 4 e 4A", "trecho": "Cláusula 4: ..."}
    ]
  },
  "parecer": {
    "parecer_resumido": "Contrato aceitável com ajustes de SLA.",
    "parecer_detalhado": "...texto longo...",
    "contra_proposta": {
      "clausula_vigencia": "24 meses com renovação automática",
      "clausula_multa": "Multa limitada a 10% do valor mensal",
      "clausula_obrigacoes": "Definir RTO/RPO" ,
      "clausula_resolucao_conflitos": "Mediação antes de arbitragem"
    }
  },
  "jurisprudencia": [
    {
      "termo": "contrato",
      "url": "https://www.jusbrasil.com.br/jurisprudencia/busca?q=contrato",
      "fonte": "Jusbrasil"
    },
    {
      "termo": "multa",
      "url": "https://www.jusbrasil.com.br/jurisprudencia/busca?q=multa",
      "fonte": "Jusbrasil"
    },
    {
      "termo": "rescisão",
      "url": "https://www.jusbrasil.com.br/jurisprudencia/busca?q=rescis%C3%A3o",
      "fonte": "Jusbrasil"
    }
  ]
}
```

## Como renderizar no front
- Trate listas vazias como ausência de conteúdo.
- Para `avisos` (analista): exiba um bloco destacado; se contiver "sem ocorrencias", mostrar como ausência de achados críticos.
- Para `clausulas` longas, use acordeão/colapso.
- **Para `jurisprudencia`** *(NOVO)*: renderize como lista de links clicáveis que abrem em nova aba.
  ```javascript
  data.jurisprudencia?.forEach(jur => {
    const link = `<a href="${jur.url}" target="_blank">${jur.termo}</a>`;
    // adicionar ao DOM
  });
  ```
- Sempre mantenha um painel de JSON bruto para debug.

## Erros comuns de API
- `401` token ausente/expirado
- `404` doc não encontrado ou sem permissão, template não encontrado
- `422` payload inválido

## Observação sobre formatação
Os textos podem seguir as instruções/modelos do usuário; portanto, mantenha componentes flexíveis a variação de tamanho e estilo (bullets, parágrafos).