# Previsão RS — @previsaors

Motor meteorológico baseado no repositório `pabloramoa-dev/previsao-modelo`. Nome do repositório independente previsto: `pabloramoa-dev/previsao-rs`.

**Reels:** Bira às 06h para hoje e Bia às 18h para amanhã, horário de Brasília/RS (`America/Sao_Paulo`). Estúdio HyperFrames vertical, vozes Kokoro, 6 regiões no quadro, chuva em milímetros e maior evento destacado sem inventar dados. Os ganchos alternam entre âncoras ao longo da semana. Os outros municípios são reservas editoriais (tier 2).

| Região | Âncora | Outras localidades |
|---|---|---|
| Metropolitana e Vales | Porto Alegre | Canoas, Novo Hamburgo, São Leopoldo, Guaíba, Lajeado, Estrela, Encantado, Montenegro |
| Serra e Campos de Cima | Caxias do Sul | Gramado, Bento Gonçalves, Vacaria, São José dos Ausentes, Farroupilha |
| Litoral Norte | Tramandaí | Torres, Capão da Canoa, Osório, Imbé |
| Sul e Campanha | Pelotas | Rio Grande, Bagé, Sant'Ana do Livramento, Santa Vitória do Palmar, Canguçu |
| Centro e Fronteira | Santa Maria | Santa Cruz do Sul, Cachoeira do Sul, Venâncio Aires, Uruguaiana, Alegrete, São Borja |
| Norte e Noroeste | Passo Fundo | Erechim, Ijuí, Santo Ângelo, Santa Rosa, Cruz Alta |

## Apresentação no padrão do Previsão RJ

Os Reels diários seguem o motor `hyperframes/gerar_hf.py`, o mesmo formato de telejornal do `previsao-rj`. O Bira apresenta **hoje às 06h** e a Bia apresenta **amanhã às 18h**. Ambos utilizam exatamente os mesmos presets Kokoro e direção de animação, layout de telão, HUD, lower thirds, cartões com números, quadro de seis regiões, chuva em milímetros, legenda karaokê, SFX, CTA e capa.

**A primeira frase já apresenta uma previsão real** (cidade, mínima, máxima e chuva). Não existe apresentação pessoal nem frase genérica sobre incerteza. Os boletins são mantidos na janela de 25 a 38 segundos, com gate de QA de 40 segundos.

O motor avulso `hyperframes/comunicado_dupla.py` continua disponível somente para comunicados especiais com Bira e Bia conversando. **Não deve ser usado como formato do Reel diário**, porque sua apresentação é diferente da usada no RJ.

Para comparar dois pilotos reais sem publicar, execute **Actions → Piloto RS - mesmo padrão do Previsão RJ (sem publicar)**. A matriz gera MP4 e capa separados de Bira/manhã e Bia/noite, usando o mesmo motor diário, o mesmo gate de qualidade e as seis regiões próprias do RS.

## Peculiaridades do estado
- Serra e Campos de Cima: frio, geada, nevoeiro e possibilidade de neve **somente com evidência**.
- Vales do Taquari, Caí, Sinos, Jacuí e Rio Uruguai, além do Guaíba: acompanhar níveis hidrológicos oficiais; **mm previstos não equivalem a enchentes confirmadas**.
- Litoral: vento, ressaca e condições marítimas; não inventar altura de ondas com coleta marítima desabilitada.
- Campanha, Fronteira Oeste e Noroeste: temporais, granizo, calor e estiagem conforme a fonte e a estação do ano.
- Frentes frias e ciclones extratropicais: destacar município, faixa horária, incerteza e validade; evitar sensacionalismo.

Fontes: [MET Norway](https://api.met.no) para previsão (crédito e licença CC BY 4.0); [INMET](https://avisos.inmet.gov.br/), [Defesa Civil RS](https://www.defesacivil.rs.gov.br/avisos-e-boletins), [ClimaRS](https://clima.rs.gov.br/) para avisos e monitoramento oficial.

## Monitor às 14h
`monitor_alertas_rs.yml` roda todos os dias às 17:00 UTC = 14:00 no RS e consulta avisos ativos do INMET. Seleciona municípios com geocodes IBGE 43, valida vigência, deduplica e produz JSON e resumo. **Não publica automaticamente**, pois a conta @previsaors ainda não está integrada e os avisos da Defesa Civil/níveis dos rios exigem confirmação separada.

## Ativação do novo repositório
1. ✅ Repositório independente `pabloramoa-dev/previsao-rs` criado (privado), com histórico Git próprio e a branch `main` como principal. Origem: branch `canal/previsao-rs` do `previsao-modelo`, que não foi alterado.
2. Em Actions, rodar CI, coleta e validação do estúdio (sem publicar) e conferir os MP4.
3. Criar/conectar Instagram profissional `@previsaors`; definir variable `EXPECTED_IG_USERNAME=previsaors` e secrets `IG_USER_ID`, `IG_ACCESS_TOKEN`, `GH_PAT_SECRETS` exclusivos do canal.
4. Só depois de validação e publicação manual usar `AUTOMATION_ENABLED=true`.
5. Se usar cron-job.org como gatilho principal, despachar `reel_manha` às 05h35 e `reel_noite` às 17h35 no fuso local. O GitHub possui gatilhos de reserva.

Nunca reutilizar credenciais Meta de outro canal.


## Identificação das cidades no quadro e rodízio

Em cada Reel aparecem **seis cidades reais**, uma de cada região do RS. O
quadro principal mostra o **nome da cidade em letras grandes**, a **região logo
abaixo**, as temperaturas e os milímetros de chuva previstos exatamente para
aquele município. A locução fala os nomes das cidades, nunca apenas a região.

A coleta dos Reels da manhã, da noite e do piloto usa
`python -m scripts.collect_live output/snapshot.json --rodizio`.
A cada dia, o rodízio escolhe outra cidade cadastrada em cada região;
Bira e Bia do mesmo dia cobrem as mesmas cidades. Não são introduzidos
números fictícios: se faltar previsão, a coleta falha e não publica.

O convite final incentiva os moradores a seguirem **@previsaors** para
verem sua cidade em edições futuras.
