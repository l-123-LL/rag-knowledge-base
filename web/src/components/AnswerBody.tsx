import type { ReactNode } from 'react'

/**
 * 轻量 Markdown 渲染：只处理模型实际会输出的四种结构——段落、无序列表、
 * 有序列表、行内加粗与行内代码。
 *
 * 为什么不引第三方库：模型输出受系统提示词约束，结构很有限；自己实现 60 行
 * 就能覆盖，且不会为了渲染一段话引入一个解析器和它的安全边界。
 * 注意这里不解析 HTML，所有内容都作为纯文本渲染，避免注入。
 */

type Block =
  | { type: 'paragraph'; lines: string[] }
  | { type: 'ul' | 'ol'; items: string[] }

const BULLET_RE = /^\s*[-*·]\s+/
const ORDERED_RE = /^\s*\d+[.)、]\s+/

function toBlocks(text: string): Block[] {
  const blocks: Block[] = []

  for (const rawLine of text.replace(/\r\n/g, '\n').split('\n')) {
    const line = rawLine.trimEnd()
    const bullet = BULLET_RE.test(line)
    const ordered = ORDERED_RE.test(line)

    if (!line.trim()) {
      // 空行结束当前块
      const last = blocks[blocks.length - 1]
      if (last && last.type === 'paragraph') {
        blocks.push({ type: 'paragraph', lines: [] })
      }
      continue
    }

    if (bullet || ordered) {
      const type = bullet ? 'ul' : 'ol'
      const item = line.replace(bullet ? BULLET_RE : ORDERED_RE, '')
      const last = blocks[blocks.length - 1]
      if (last && last.type === type) {
        last.items.push(item)
      } else {
        blocks.push({ type, items: [item] })
      }
      continue
    }

    const last = blocks[blocks.length - 1]
    if (last && last.type === 'paragraph' && last.lines.length > 0) {
      last.lines.push(line)
    } else {
      blocks.push({ type: 'paragraph', lines: [line] })
    }
  }

  return blocks.filter(
    (block) => block.type !== 'paragraph' || block.lines.some((line) => line.trim()),
  )
}

/** 行内处理：**加粗**、`代码`。其余内容按纯文本渲染。 */
function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = []
  const pattern = /(\*\*[^*]+\*\*|`[^`]+`)/g
  let cursor = 0
  let match: RegExpExecArray | null
  let index = 0

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > cursor) {
      nodes.push(text.slice(cursor, match.index))
    }

    const token = match[0]
    if (token.startsWith('**')) {
      nodes.push(<strong key={`${keyPrefix}-b${index}`}>{token.slice(2, -2)}</strong>)
    } else {
      nodes.push(<code key={`${keyPrefix}-c${index}`}>{token.slice(1, -1)}</code>)
    }

    cursor = match.index + token.length
    index += 1
  }

  if (cursor < text.length) {
    nodes.push(text.slice(cursor))
  }

  return nodes
}

export function AnswerBody({ text }: { text: string }) {
  const blocks = toBlocks(text)

  return (
    <div className="answer-body">
      {blocks.map((block, blockIndex) => {
        if (block.type === 'paragraph') {
          return (
            <p key={`p-${blockIndex}`}>
              {renderInline(block.lines.join('\n'), `p${blockIndex}`)}
            </p>
          )
        }

        const ListTag = block.type === 'ul' ? 'ul' : 'ol'
        return (
          <ListTag key={`l-${blockIndex}`}>
            {block.items.map((item, itemIndex) => (
              <li key={`i-${blockIndex}-${itemIndex}`}>
                {renderInline(item, `i${blockIndex}-${itemIndex}`)}
              </li>
            ))}
          </ListTag>
        )
      })}
    </div>
  )
}
