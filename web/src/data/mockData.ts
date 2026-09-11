import type { Citation, MockConversation, Source } from '../types'

// 示例来源：用状态展示 RAG 资料导入的不同结果，未来会替换为真实接口数据。
export const mockSources: Source[] = [
  {
    id: 'nhc-influenza-2025',
    title: '流行性感冒诊疗方案（2025年版）',
    category: '诊疗指南',
    url: 'https://www.nhc.gov.cn/wjw/ylyjs/202501/ac113876c97c47a7bd8c03c3c05ffa08.shtml',
    status: 'indexed',
    updatedAt: '2025-01-20',
    description:
      '国家卫生健康委发布的流感规范化诊疗方案，涵盖诊断、抗病毒治疗时机与重症识别。',
  },
  {
    id: 'nhc-obesity-2024',
    title: '肥胖症诊疗指南（2024年版）',
    category: '诊疗指南',
    url: 'https://www.gov.cn/zhengce/zhengceku/202410/content_6981734.htm',
    status: 'indexed',
    updatedAt: '2024-10-12',
    description:
      '国家卫生健康委制定的肥胖症诊疗指南，包含诊断标准、评估方法与综合干预策略。',
  },
  {
    id: 'basic-hypertension-guide',
    title: '国家基层高血压防治管理指南',
    category: '慢病防治',
    url: 'https://www.nhc.gov.cn/',
    status: 'pending',
    updatedAt: '待确认',
    description:
      '面向基层医疗机构的高血压防治与管理资料，用于展示待处理来源状态。',
  },
  {
    id: 'nmpa-drug-instructions',
    title: '国家药监局化学药品说明书',
    category: '药品说明',
    url: 'https://www.nmpa.gov.cn/datasearch/',
    status: 'failed',
    updatedAt: '导入失败',
    description:
      '国家药监局公开的药品说明书数据，用于展示来源导入失败状态。',
  },
  {
    id: 'who-zh-health-topics',
    title: '世界卫生组织中文健康专题',
    category: '权威科普',
    url: 'https://www.who.int/zh/news-room/fact-sheets',
    status: 'pending',
    updatedAt: '待处理',
    description:
      '世界卫生组织中文事实页与健康专题，可作为后续补充的公开科普来源。',
  },
]

const fluCitations: Citation[] = [
  {
    id: 'flu-cite-1',
    title: '流行性感冒诊疗方案（2025年版）',
    url: 'https://www.nhc.gov.cn/wjw/ylyjs/202501/ac113876c97c47a7bd8c03c3c05ffa08.shtml',
    location: '抗病毒治疗章节',
    snippet:
      '重症或有重症流感高危因素的患者，应尽早给予抗流感病毒治疗，不必等待病毒检测结果。',
    score: 0.94,
  },
]

const hypertensionCitations: Citation[] = [
  {
    id: 'htn-cite-1',
    title: '国家基层高血压防治管理指南',
    url: 'https://www.nhc.gov.cn/',
    location: '治疗与管理章节',
    snippet:
      '高血压管理应结合生活方式干预和规范药物治疗，定期随访并评估血压达标情况。',
    score: 0.91,
  },
]

const medicationCitations: Citation[] = [
  {
    id: 'drug-cite-1',
    title: '国家药监局化学药品说明书',
    url: 'https://www.nmpa.gov.cn/datasearch/',
    location: '注意事项章节',
    snippet:
      '用药前应核对药品名称、适应症、用法用量与禁忌，出现严重不良反应应及时就医。',
    score: 0.89,
  },
]

const obesityCitations: Citation[] = [
  {
    id: 'obesity-cite-1',
    title: '肥胖症诊疗指南（2024年版）',
    url: 'https://www.gov.cn/zhengce/zhengceku/202410/content_6981734.htm',
    location: '诊断与评估章节',
    snippet:
      '肥胖症的诊断需综合体重指数、腰围及代谢异常等因素进行评估，而非仅凭体重判断。',
    score: 0.92,
  },
]

export const mockConversations: MockConversation[] = [
  {
    id: 'flu-treatment',
    question: '成人流感的抗病毒治疗时机是什么？',
    keywords: ['流感', '抗病毒', '奥司他韦', '治疗时机'],
    answer:
      '根据示例资料，对于重症流感患者或有重症高危因素的患者，应尽早给予抗流感病毒治疗，不必等待病毒检测结果。轻症且无高危因素者可在医生评估后决定是否用药。',
    citations: fluCitations,
  },
  {
    id: 'hypertension-management',
    question: '高血压患者应该如何进行日常管理？',
    keywords: ['高血压', '降压', '血压', '管理'],
    answer:
      '示例资料显示，高血压管理应结合低盐饮食、规律运动、控制体重等生活方式干预，并遵医嘱规范使用降压药物，同时定期监测血压和复诊。',
    citations: hypertensionCitations,
  },
  {
    id: 'medication-precautions',
    question: '用药前需要注意哪些事项？',
    keywords: ['用药', '药品', '注意事项', '说明书'],
    answer:
      '示例资料提示，用药前应核对药品名称、适应症、用法用量、禁忌和不良反应，避免自行加量或混用多种药物；出现严重不适时应及时停药并就医。',
    citations: medicationCitations,
  },
  {
    id: 'obesity-diagnosis',
    question: '肥胖症应该如何诊断？',
    keywords: ['肥胖', 'bmi', '体重指数', '诊断'],
    answer:
      '示例资料显示，肥胖症的诊断需要综合体重指数、腰围以及血压、血糖、血脂等代谢异常情况进行评估，而不是单纯依据体重数字判断。',
    citations: obesityCitations,
  },
]

// 用关键词做最简单的本地匹配；真实版本会改成后端检索接口。
export function findMockAnswer(question: string): MockConversation | undefined {
  const normalized = question.toLowerCase().replace(/\s+/g, '')

  return mockConversations.find((item) =>
    item.keywords.some((keyword) =>
      normalized.includes(keyword.toLowerCase().replace(/\s+/g, '')),
    ),
  )
}
