export type Language = 'zh' | 'en';
export const chinese = {
  title: 'Scientific Parallax · 科学视差',
  description:
    '让 AI 不只寻找答案，也参与重新审视问题、表征与测量。一个以独立证据为约束的探索性研究倡议。',
  socialDescription: '换个视角，问题也会改变。探索表征、问题、测量与独立证据。',
  skip: '跳至正文',
  home: 'Scientific Parallax 首页',
  brand: '科学视差',
  brandSub: 'Scientific Parallax',
  navigation: '主导航',
  languageNavigation: '选择语言',
  nav: ['关注什么', '如何探索', '证据边界'],
  archive: '研究记录',
  kind: 'AI 与科学探索 · 一个开放的研究倡议',
  headline: ['换个视角，', '问题也会改变。'],
  intro: '让 AI 不只在既有地图中寻找答案，\n也参与重新审视地图的画法。',
  start: '从关注点开始',
  world: '世界没有改变。',
  perspectives: '描述世界的方式，未必只有一种。',
  readPremise: '向下阅读项目立场',
  premiseLabel: '为什么是视差',
  premiseTitle: ['有时，缺少的不是答案。', '而是另一种提问方式。'],
  premise: [
    '当变量、任务和评价指标已经给定，预测能力的提升，并不必然改变我们理解现象的方式。我们关注更早的一层：如何组织经验，为什么提出这些问题？',
    '“视差”是一种方法隐喻。让不同表征面对同一个世界，暴露单一视角中不易察觉的假设。然后，让实验判断这些差异是否有价值。',
  ],
  focusLabel: '我们的关注点',
  focusIntro: '把科学探索的前提，\n也变成可以研究的对象。',
  interests: [
    {
      word: 'Representation',
      title: '重新选择，描述世界的语言。',
      tag: '表征',
      body: '对象、关系、变量与尺度，不必永远是研究的既定前提。我们关心新的表示能否统一异常，产生旧表示无法给出的可检验预测。',
      limit: '改个名字，还不是新概念。',
    },
    {
      word: 'Questions',
      title: '让解释，生长出新的问题。',
      tag: '问题生成',
      body: '什么实验会真正改变判断？问题需要说明改变什么、测量什么，以及竞争解释分别预测什么，而不只是生成一个新奇问句。',
      limit: '制造分歧，还不是科学价值。',
    },
    {
      word: 'Measurement',
      title: '把观察者，放回观察之中。',
      tag: '测量',
      body: '数据经过仪器、采样与处理才成为观测。异常究竟属于被测系统，还是观察它的方式？测量模型需要成为解释的一部分。',
      limit: '预测准确，还不等于归因正确。',
    },
    {
      word: 'Evidence',
      title: '给每个想法，留下退出的条件。',
      tag: '独立证据',
      body: '先封存预测，再面对实验。记录修正、适用范围与失败，用独立证据决定解释的去留，也允许我们自己的方法被推翻。',
      limit: '动听的叙事，还不是科学发现。',
    },
  ],
  methodLabel: '一种工作假说',
  methodTitle: ['解释改变问题。', '证据改变解释。'],
  methodIntro:
    '不是先决定什么是“好范式”，\n而是让想法有机会被检验、修正和淘汰。',
  steps: [
    ['保留竞争解释', '让不同的可执行表征并存。'],
    ['提出区分性问题', '找到预测真正分开的实验。'],
    ['获得外部证据', '先封存预测，再观测与干预。'],
    ['修正解释与问题', '记录谱系，也保留失败。'],
  ],
  pending: '仍待检验',
  methodLimit:
    '范式与问题共进化，只是一种实现候选，不是已被证明的优势。算法与应用领域可以更换；可检验性与独立证据不能省略。',
  boundaryLabel: '我们能说到哪里',
  boundaryTitle: ['把愿景，', '和证据分开。'],
  boundaryIntro: '这是一个长期关注方向，\n不是一项已经完成的科学突破。',
  audit: '查看实验与审计',
  boundaries: [
    {
      tag: '范围',
      title: '模拟中的成功，不等于自然界的发现。',
      body: '已有探索展示了受限合成世界中的结构恢复能力，不能外推为新规律发现。',
    },
    {
      tag: '归因',
      title: '能力结果，不等于独特的算法优势。',
      body: '共进化的独特优势尚未得到支持，旧机制归因已被审计收紧。',
    },
    {
      tag: '记录',
      title: '负结果，也属于项目的知识。',
      body: '历史停止结论保持不变。新的研究，需要新的问题与独立检验。',
    },
  ],
  invitationLabel: '保持问题开放',
  invitationTitle: ['从一个疑问，', '开始对话。'],
  invitation:
    '我们正在整理概念、反例与证据标准，\n暂不绑定某个具体课题。\n如果你也关心这些问题，欢迎带来另一种视角。',
  email: '发送邮件',
  discuss: '交流想法',
  footer: '保持多种视角。接受同一个世界的检验。',
  observation: {
    heading: 'ONE OBJECT. DIFFERENT PROJECTIONS.',
    titlePrefix: '同一个环面的',
    titleSuffix: '投影',
    description:
      '固定数学环面在不同角度的正交投影，用于说明表征变化。不是实验数据，也不代表发现结果。',
    object: '同一个对象',
    ways: '三种观察方式',
    switch: '切换视角',
    label: '观察环面的投影视角',
    disclaimer: '数学示意，不是实验数据。视角差异本身不构成证据。',
    views: {
      oblique: {
        label: '斜视',
        description: '改变观察的角度，环面的层次关系显现。',
      },
      front: {
        label: '正面',
        description: '从正面看，同一个环面呈现为同心轮廓。',
      },
      side: {
        label: '侧面',
        description: '从侧面看，投影压缩了深度，原本的孔洞不再可见。',
      },
    },
  },
};
export const english: typeof chinese = {
  title: 'Scientific Parallax — A different way to ask',
  description:
    'Exploring how AI can rethink scientific questions, representations and measurement, with independent evidence as the constraint.',
  socialDescription:
    'Change the perspective. Change the question. Exploring representations, questions, measurement and independent evidence.',
  skip: 'Skip to content',
  home: 'Scientific Parallax home',
  brand: 'Scientific Parallax',
  brandSub: 'An open research initiative',
  navigation: 'Main navigation',
  languageNavigation: 'Choose language',
  nav: ['Our focus', 'Our approach', 'Evidence & limits'],
  archive: 'Research archive',
  kind: 'AI & scientific discovery · An open research initiative',
  headline: ['Change the perspective.', 'Change the question.'],
  intro:
    'AI should do more than find answers on an existing map.\nIt could help us reconsider how the map is drawn.',
  start: 'Explore our focus',
  world: 'The world has not changed.',
  perspectives: 'There may be more than one way to describe it.',
  readPremise: 'Read our premise',
  premiseLabel: 'Why parallax?',
  premiseTitle: [
    'Sometimes, what is missing is not an answer.',
    'It is another way to ask.',
  ],
  premise: [
    'When variables, tasks and evaluation criteria are already fixed, better predictions do not necessarily change how we understand a phenomenon. We look one step earlier: how do we organize experience, and why do we ask these questions?',
    'Parallax is a methodological metaphor. Let different representations face the same world, exposing assumptions that a single perspective may hide. Then let experiments determine whether those differences matter.',
  ],
  focusLabel: 'What we care about',
  focusIntro:
    'Make the premises of scientific inquiry\npart of the inquiry itself.',
  interests: [
    {
      word: 'Representation',
      title: 'Reconsider the language used to describe the world.',
      tag: 'Concepts',
      body: 'Objects, relations, variables and scales need not remain fixed premises. Can a new representation unify anomalies and produce testable predictions that the old one cannot?',
      limit: 'A new name is not yet a new concept.',
    },
    {
      word: 'Questions',
      title: 'Let explanations open up new questions.',
      tag: 'Inquiry',
      body: 'Which experiment would actually change our judgment? A question must specify what to change, what to measure and what competing explanations predict—not merely sound novel.',
      limit: 'Disagreement alone is not scientific value.',
    },
    {
      word: 'Measurement',
      title: 'Put the observer back into the observation.',
      tag: 'Observation',
      body: 'Instruments, sampling and processing shape what becomes an observation. Does an anomaly belong to the system, or to the way we observe it? The measurement model must be part of the explanation.',
      limit: 'Accurate prediction is not correct attribution.',
    },
    {
      word: 'Evidence',
      title: 'Give every idea a condition under which it must go.',
      tag: 'Independent tests',
      body: 'Commit to predictions before running experiments. Record revisions, scope and failures. Let independent evidence decide which explanations survive—and allow our own methods to be refuted.',
      limit: 'A compelling story is not a scientific discovery.',
    },
  ],
  methodLabel: 'A working hypothesis',
  methodTitle: [
    'Explanations change questions.',
    'Evidence changes explanations.',
  ],
  methodIntro:
    'Rather than decide what a “good paradigm” is in advance,\ngive ideas a chance to be tested, revised and rejected.',
  steps: [
    [
      'Retain competing explanations',
      'Keep different executable representations in play.',
    ],
    [
      'Ask discriminating questions',
      'Find experiments where predictions genuinely diverge.',
    ],
    [
      'Obtain external evidence',
      'Commit to predictions, then observe and intervene.',
    ],
    [
      'Revise explanations and questions',
      'Track lineages, including their failures.',
    ],
  ],
  pending: 'Still to be tested',
  methodLimit:
    'Coevolution of paradigms and questions is one candidate implementation, not a demonstrated advantage. Algorithms and application domains may change; testability and independent evidence are non-negotiable.',
  boundaryLabel: 'The limits of our claims',
  boundaryTitle: ['Separate the ambition', 'from the evidence.'],
  boundaryIntro:
    'This is a long-term research direction,\nnot an accomplished scientific breakthrough.',
  audit: 'Read experiments & audits',
  boundaries: [
    {
      tag: 'Scope',
      title: 'Success in simulation is not discovery in nature.',
      body: 'Existing explorations demonstrate structural recovery in constrained synthetic worlds. They do not establish the discovery of new natural laws.',
    },
    {
      tag: 'Attribution',
      title: 'A capability result is not a unique algorithmic advantage.',
      body: 'A distinctive advantage for coevolution has not been supported. Audits have narrowed earlier claims about the mechanism behind the results.',
    },
    {
      tag: 'Record',
      title: 'Negative results are part of what the project knows.',
      body: 'Previous stop decisions stand. New research requires new questions and independent tests.',
    },
  ],
  invitationLabel: 'Keep the questions open',
  invitationTitle: ['Start a conversation', 'with a question.'],
  invitation:
    'We are organizing concepts, counterexamples and standards of evidence,\nwithout committing to a specific research problem yet.\nIf these questions resonate, bring another perspective.',
  email: 'Send an email',
  discuss: 'Join the conversation',
  footer: 'Keep multiple perspectives. Test them against the same world.',
  observation: {
    heading: 'ONE OBJECT. DIFFERENT PROJECTIONS.',
    titlePrefix: '',
    titleSuffix: ' projection of the same torus',
    description:
      'Orthographic projections of a fixed mathematical torus illustrate a change in representation. This is not experimental data or a discovery result.',
    object: 'The same object',
    ways: 'Three ways to observe',
    switch: 'Change view',
    label: 'Choose a torus projection',
    disclaimer:
      'Mathematical illustration, not experimental data. A different view is not evidence.',
    views: {
      oblique: {
        label: 'Oblique',
        description:
          'An oblique view reveals the layered structure of the torus.',
      },
      front: {
        label: 'Front',
        description:
          'From the front, the same torus appears as concentric outlines.',
      },
      side: {
        label: 'Side',
        description:
          'From the side, depth is compressed and the central hole is no longer visible.',
      },
    },
  },
};
export function getCopy(language: Language) {
  return language === 'en' ? english : chinese;
}
export function languageFromPath(path: string): Language {
  return path === '/en' || path.startsWith('/en/') ? 'en' : 'zh';
}
export function languagePath(language: Language) {
  return language === 'en' ? '/en/' : '/';
}
