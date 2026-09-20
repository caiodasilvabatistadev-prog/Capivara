export type OfficialSource = { date: string; label: string; url: string };

export type DirtyRecord = {
  detail: string; name: string; photo: string; photoPosition: string; photoSize?: string;
  slug: string; sources: OfficialSource[]; tags: string[]; lifeStatus?: "falecido" | "vivo";
};

export const dirtyRecords: DirtyRecord[] = [
  {
    slug: "jose-maria-marin", name: "José Maria Marin", lifeStatus: "falecido",
    tags: ["Condenado", "Preso anteriormente", "Falecido"],
    detail: "Ex-governador de São Paulo e ex-presidente da CBF. A Justiça dos Estados Unidos o condenou a quatro anos de prisão por associação criminosa e corrupção. A Federação Paulista de Futebol confirmou seu falecimento em 20 de julho de 2025.",
    sources: [
      { date: "22/08/2018", label: "Departamento de Justiça dos Estados Unidos", url: "https://www.justice.gov/usao-edny/pr/former-brazilian-soccer-official-sentenced-four-years-imprisonment-racketeering-and" },
      { date: "20/07/2025", label: "Federação Paulista de Futebol", url: "https://futebolpaulista.com.br/Noticias/Detalhe.aspx?Noticia=29675" },
    ],
    photo: "https://commons.wikimedia.org/wiki/Special:FilePath/Jos%C3%A9%20Maria%20Marin%20in%202012.jpg", photoPosition: "center top",
  },
  {
    slug: "jair-bolsonaro", name: "Jair Bolsonaro",
    tags: ["Inelegível", "Condenado", "Preso", "Domiciliar"],
    detail: "O TSE declarou sua inelegibilidade por oito anos a partir das Eleições 2022. O STF também registra condenação definitiva a 27 anos e 3 meses e informa que, em 3 de julho de 2026, manteve o cumprimento da pena em prisão domiciliar humanitária.",
    sources: [
      { date: "30/06/2023", label: "Tribunal Superior Eleitoral", url: "https://www.tse.jus.br/comunicacao/noticias/2023/Junho/por-maioria-de-votos-tse-declara-bolsonaro-inelegivel-por-8-anos" },
      { date: "03/07/2026", label: "Supremo Tribunal Federal", url: "https://noticias.stf.jus.br/postsnoticias/stf-mantem-ex-presidente-bolsonaro-em-prisao-domiciliar/" },
    ],
    photo: "https://upload.wikimedia.org/wikipedia/commons/e/ed/Jair_Bolsonaro_em_maio_de_2019.jpg", photoPosition: "center top",
  },
  {
    slug: "walter-braga-netto", name: "Walter Braga Netto", tags: ["Inelegível"],
    detail: "O TSE declarou inelegibilidade por oito anos contados a partir das Eleições 2022, no julgamento sobre abuso de poder nas comemorações do Bicentenário da Independência.",
    sources: [{ date: "31/10/2023", label: "Tribunal Superior Eleitoral", url: "https://www.tse.jus.br/comunicacao/noticias/2023/Outubro/tse-declara-inelegiveis-bolsonaro-e-braga-netto-por-abuso-de-poder-no-bicentenario-da-independencia" }],
    photo: "https://upload.wikimedia.org/wikipedia/commons/5/55/Foto_Oficial_do_Sr_Ministro_da_Defesa_Walter_Braga_Netto.jpg", photoPosition: "center top",
  },
  {
    slug: "claudio-castro", name: "Cláudio Castro", tags: ["Inelegível"],
    detail: "O TSE informou que rejeitou recursos e manteve a inelegibilidade por abuso de poder político e econômico, condutas vedadas e captação ilícita de recursos nas Eleições 2022.",
    sources: [{ date: "02/06/2026", label: "Tribunal Superior Eleitoral", url: "https://www.tse.jus.br/comunicacao/noticias/2026/Junho/tse-mantem-inelegibilidade-de-claudio-castro-ex-governador-do-rio" }],
    photo: "https://upload.wikimedia.org/wikipedia/commons/9/9b/Cl%C3%A1udio_Castro%2C_governador_do_Rio_de_Janeiro.jpg", photoPosition: "center top",
  },
  {
    slug: "antonio-denarium", name: "Antonio Denarium", tags: ["Inelegível"],
    detail: "O TSE confirmou a cassação e declarou o ex-governador de Roraima inelegível pelo prazo de oito anos.",
    sources: [{ date: "09/04/2026", label: "Tribunal Superior Eleitoral", url: "https://www.tse.jus.br/comunicacao/noticias/2026/Abril/tse-cassa-mandato-do-governador-e-determina-eleicoes-diretas-em-roraima" }],
    photo: "https://upload.wikimedia.org/wikipedia/commons/e/ea/Antonio_Denarium_%28cropped%29.jpg", photoPosition: "center top", photoSize: "68% auto",
  },
  {
    slug: "roberto-jefferson", name: "Roberto Jefferson", tags: ["Condenado", "Preso", "Domiciliar"],
    detail: "O STF informou o trânsito em julgado da condenação e o início do cumprimento da pena. A fonte registra prisão domiciliar com tornozeleira eletrônica.",
    sources: [{ date: "02/02/2026", label: "Supremo Tribunal Federal", url: "https://noticias.stf.jus.br/postsnoticias/stf-determina-inicio-do-cumprimento-da-pena-imposta-a-ex-deputado-roberto-jefferson/" }],
    photo: "https://hojepr.com/wp-content/uploads/2022/09/roberto-jeferson.jpg", photoPosition: "center top",
  },
  {
    slug: "carla-zambelli", name: "Carla Zambelli", tags: ["Condenada", "Presa anteriormente", "Liberta na Itália"],
    detail: "O STF decretou o início definitivo da pena de 10 anos em regime fechado. Ela foi presa na Itália em julho de 2025, mas a Justiça italiana negou a extradição e a libertou em maio de 2026; por isso o cartão não a apresenta como presa atualmente.",
    sources: [
      { date: "07/06/2025", label: "Supremo Tribunal Federal", url: "https://noticias.stf.jus.br/postsnoticias/stf-decreta-prisao-definitiva-de-carla-zambelli-e-walter-delgatti/" },
      { date: "22/05/2026", label: "Agência Brasil", url: "https://agenciabrasil.ebc.com.br/justica/noticia/2026-05/zambelli-e-libertada-na-italia-apos-tribunal-negar-extradicao" },
    ],
    photo: "https://commons.wikimedia.org/wiki/Special:FilePath/Carla%20Zambelli%20%28cropped%29.jpg", photoPosition: "center top", photoSize: "92% auto",
  },
  {
    slug: "arthur-do-val", name: "Arthur do Val (Mamãe Falei)", tags: ["Inelegível", "Mandato cassado"],
    detail: "A Assembleia Legislativa de São Paulo decretou a perda do mandato por quebra de decoro parlamentar. A própria Alesp registra que a cassação tornou o ex-deputado inelegível por oito anos.",
    sources: [{ date: "20/05/2022", label: "Assembleia Legislativa de São Paulo", url: "https://www.al.sp.gov.br/repositorio/legislacao/resolucao.alesp/2022/resolucao.alesp-933-20.05.2022.html" }],
    photo: "https://commons.wikimedia.org/wiki/Special:FilePath/Arthur%20do%20Val%20%28cropped%29.jpg", photoPosition: "center top", photoSize: "68% auto",
  },
  {
    slug: "flordelis", name: "Flordelis dos Santos", tags: ["Condenada", "Presa"],
    detail: "O STJ manteve a condenação da ex-deputada federal a 50 anos de reclusão. A decisão oficial registra que ela permanece presa pelo homicídio do pastor Anderson do Carmo.",
    sources: [{ date: "18/09/2026", label: "Superior Tribunal de Justiça", url: "https://www.stj.jus.br/sites/portalp/Paginas/Comunicacao/Noticias/2026/18092026-Tribunal-mantem-condenacao-de-ex-deputada-Flordelis-a-50-anos-de-prisao.aspx" }],
    photo: "https://commons.wikimedia.org/wiki/Special:FilePath/Flordelis%20em%20mar%C3%A7o%20de%202019.jpg", photoPosition: "center top", photoSize: "94% auto",
  },
  {
    slug: "sergio-cabral", name: "Sérgio Cabral Filho", tags: ["Condenado", "Preso anteriormente", "Prisão revogada"],
    detail: "O TRF2 registra condenação a 20 anos, 4 meses e 21 dias e também informa que a prisão preventiva domiciliar foi revogada. O cartão preserva as duas informações para não sugerir que ele esteja preso atualmente.",
    sources: [{ date: "2024", label: "Tribunal Regional Federal da 2ª Região", url: "https://www.trf2.jus.br/trf2/noticia/2024/trf2-revoga-prisao-domiciliar-de-sergio-cabral-seguindo-entendimento-do-supremo" }],
    photo: "https://commons.wikimedia.org/wiki/Special:FilePath/Sergiocabral2006.jpg", photoPosition: "center top", photoSize: "88% auto",
  },
];
