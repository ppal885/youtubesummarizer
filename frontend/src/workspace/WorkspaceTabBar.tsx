import { ActionGroup, Item } from '@adobe/react-spectrum'
import type { Key } from '@react-types/shared'

export const WORKSPACE_TAB_IDS = ['summary', 'ask', 'notes', 'flashcards', 'quiz'] as const
export type WorkspaceTabId = (typeof WORKSPACE_TAB_IDS)[number]

const TAB_META: { id: WorkspaceTabId; label: string }[] = [
  { id: 'summary', label: 'Summary' },
  { id: 'ask', label: 'Ask AI' },
  { id: 'notes', label: 'Notes' },
  { id: 'flashcards', label: 'Flashcards' },
  { id: 'quiz', label: 'Quiz' },
]

type Props = {
  active: WorkspaceTabId
  onChange: (id: WorkspaceTabId) => void
}

export function WorkspaceTabBar({ active, onChange }: Props) {
  return (
    <ActionGroup
      selectionMode="single"
      selectedKeys={new Set<Key>([active])}
      onSelectionChange={(keys) => {
        const next = [...keys][0]
        if (next && WORKSPACE_TAB_IDS.includes(next as WorkspaceTabId)) {
          onChange(next as WorkspaceTabId)
        }
      }}
      aria-label="Workspace tools"
      isQuiet
      density="compact"
      overflowMode="wrap"
    >
      {TAB_META.map((tab) => (
        <Item key={tab.id} textValue={tab.label}>
          {tab.label}
        </Item>
      ))}
    </ActionGroup>
  )
}
