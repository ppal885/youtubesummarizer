import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { Flex, View } from '@adobe/react-spectrum'
import { useLocation } from 'react-router-dom'
import { AssistantRail } from './AssistantRail'
import type { NavigationItem } from './navigation'
import { readSidebarCollapsed, Sidebar, writeSidebarCollapsed } from './Sidebar'
import { Topbar } from './Topbar'

type Props = {
  currentItem: NavigationItem
  children: ReactNode
}

export function AppShell({ currentItem, children }: Props) {
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [assistantOpen, setAssistantOpen] = useState(false)
  const [desktopSidebarCollapsed, setDesktopSidebarCollapsed] = useState(() => readSidebarCollapsed())

  const toggleDesktopSidebar = useCallback(() => {
    setDesktopSidebarCollapsed((prev) => {
      const next = !prev
      writeSidebarCollapsed(next)
      return next
    })
  }, [])

  useEffect(() => {
    setSidebarOpen(false)
    setAssistantOpen(false)
  }, [location.pathname])

  return (
    <View width="100%" minHeight="100vh" backgroundColor="gray-50">
      <Flex direction="row" minHeight="100vh">
        <Sidebar
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          desktopCollapsed={desktopSidebarCollapsed}
          onToggleDesktopCollapsed={toggleDesktopSidebar}
        />

        <Flex direction="column" flex={1} minWidth={0}>
          <Topbar
            currentItem={currentItem}
            onOpenSidebar={() => setSidebarOpen(true)}
            onOpenAssistant={() => setAssistantOpen(true)}
            sidebarCollapsed={desktopSidebarCollapsed}
            onToggleSidebarCollapse={toggleDesktopSidebar}
          />

          <Flex direction="row" flex={1} minHeight={0} minWidth={0}>
            <View flex={1} minWidth={0} paddingX={{ base: 'size-200', M: 'size-300', L: 'size-400' }} paddingY="size-200">
              <View width="100%" marginX="auto" key={location.pathname} UNSAFE_style={{ maxWidth: 1280 }}>
                {children}
              </View>
            </View>

            <AssistantRail
              assistant={currentItem.assistant}
              open={assistantOpen}
              onClose={() => setAssistantOpen(false)}
            />
          </Flex>
        </Flex>
      </Flex>
    </View>
  )
}
