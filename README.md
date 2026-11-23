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

## Abertura curta e dupla de apresentadores

O roteiro `scripts/roteiro_piloto_dupla_rs.py` começa **na primeira frase com a previsão de Porto Alegre**: mínima, máxima e volume previsto de chuva. Não há saudação, apresentação dos nomes ou explicação das fontes no áudio. Bia e Bira alternam as seis regiões; a fonte aparece no card e na legenda. O destaque de chuva só entra quando o valor justifica. `comunicado_dupla.py` usa vozes Kokoro, lip sync, cenários, animações e efeitos HyperFrames, sem publicar.

Renderização: Actions → **Piloto RS - Bia e Bira - real - sem publicar** → Run workflow. O MP4 sai como artifact. As verificações de dados recusam números faltantes e previsões antigas.

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
