import {
  ActionButton,
  Flex,
  Heading,
  Item,
  Menu,
  MenuTrigger,
  SearchField,
  Text,
  View,
} from '@adobe/react-spectrum'
import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { ThemeToggle } from '../components/ThemeToggle'
import { UsageTrackingUI } from '../components/usage/UsageTrackingUI'
import { useAppConfig } from '../context/AppConfigContext'
import { navigationItems, type NavigationItem } from './navigation'

type Props = {
  currentItem: NavigationItem
  onOpenSidebar: () => void
  onOpenAssistant: () => void
  sidebarCollapsed: boolean
  onToggleSidebarCollapse: () => void
}

export function Topbar({
  currentItem,
  onOpenSidebar,
  onOpenAssistant,
  sidebarCollapsed,
  onToggleSidebarCollapse,
}: Props) {
  const navigate = useNavigate()
  const location = useLocation()
  const { appName, appVersion } = useAppConfig()
  const [query, setQuery] = useState('')

  useEffect(() => {
    setQuery('')
  }, [location.pathname])

  function handleSearchSubmit(q: string) {
    const normalized = q.trim().toLowerCase()
    if (!normalized) return
    const match = navigationItems.find(
      (item) =>
        item.label.toLowerCase().includes(normalized) ||
        item.description.toLowerCase().includes(normalized),
    )
    if (match) navigate(match.path)
  }

  return (
    <View
      position="sticky"
      top={0}
      zIndex={10}
      backgroundColor="gray-50"
      borderBottomWidth="thin"
      borderColor="gray-200"
    >
      <View paddingX={{ base: 'size-200', M: 'size-300' }} paddingY="size-200">
        <Flex direction="column" gap="size-150">
        <Flex alignItems="center" gap="size-150" wrap>
          <ActionButton isQuiet onPress={onOpenSidebar} aria-label="Open navigation" isHidden={{ base: false, L: true }}>
            ☰
          </ActionButton>

          <ActionButton
            isQuiet
            onPress={onToggleSidebarCollapse}
            aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            isHidden={{ base: true, L: false }}
          >
            {sidebarCollapsed ? '→' : '←'}
          </ActionButton>

          <Flex direction="column" minWidth={0} flex={1} flexBasis={0} gap="size-50">
            <Heading level={2} margin={0}>
              {currentItem.label}
            </Heading>
            <Text UNSAFE_style={{ fontSize: 13 }} slot="description">
              {currentItem.description} — {appName} v{appVersion}
            </Text>
          </Flex>

          <Flex alignItems="center" gap="size-150" wrap flexShrink={0}>
            <ThemeToggle />
            <View isHidden={{ base: true, S: false }}>
              <UsageTrackingUI compact />
            </View>
          </Flex>

          <View
            flex={2}
            flexBasis={0}
            minWidth={280}
            maxWidth={640}
            isHidden={{ base: true, XL: false }}
          >
            <SearchField
              label="Search pages"
              aria-label="Search pages"
              value={query}
              onChange={setQuery}
              onSubmit={() => handleSearchSubmit(query)}
              placeholder="Search pages and workflows"
            />
          </View>

          {currentItem.assistant ? (
            <ActionButton isQuiet onPress={onOpenAssistant} aria-label="Open assistant" isHidden={{ base: false, XL: true }}>
              ?
            </ActionButton>
          ) : null}

          <MenuTrigger>
            <ActionButton>Account</ActionButton>
            <Menu onAction={(key) => key === 'settings' && navigate('/settings')}>
              <Item key="settings">Workspace settings</Item>
              <Item key="help">Help center</Item>
            </Menu>
          </MenuTrigger>
        </Flex>

        <View isHidden={{ base: false, XL: true }}>
          <SearchField
            label="Search"
            aria-label="Search pages"
            value={query}
            onChange={setQuery}
            onSubmit={() => handleSearchSubmit(query)}
            placeholder="Search pages"
          />
        </View>
        </Flex>
      </View>
    </View>
  )
}
