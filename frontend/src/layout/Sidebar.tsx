import { ActionButton, Flex, Heading, Text, View } from '@adobe/react-spectrum'
import { useEffect, useState } from 'react'
import { Link as RouterLink, NavLink } from 'react-router-dom'
import { ProductIcon } from '../components/brand/ProductIcon'
import { navigationItems } from './navigation'

const COLLAPSE_STORAGE = 'sidebar-collapsed'

export function readSidebarCollapsed(): boolean {
  try {
    return localStorage.getItem(COLLAPSE_STORAGE) === '1'
  } catch {
    return false
  }
}

export function writeSidebarCollapsed(collapsed: boolean) {
  try {
    localStorage.setItem(COLLAPSE_STORAGE, collapsed ? '1' : '0')
  } catch {
    /* ignore */
  }
}

type Props = {
  open: boolean
  onClose: () => void
  desktopCollapsed: boolean
  onToggleDesktopCollapsed: () => void
}

const LG = '(min-width: 1024px)'

export function Sidebar({
  open,
  onClose,
  desktopCollapsed,
  onToggleDesktopCollapsed,
}: Props) {
  const [isLg, setIsLg] = useState(false)

  useEffect(() => {
    const mq = window.matchMedia(LG)
    const sync = () => setIsLg(mq.matches)
    sync()
    mq.addEventListener('change', sync)
    return () => mq.removeEventListener('change', sync)
  }, [])

  const showDrawer = !isLg && open
  const sidebarVisible = isLg || showDrawer
  /** Desktop icon-only rail: avoid asymmetric padding + start border clipping */
  const narrowRail = isLg && desktopCollapsed

  return (
    <>
      {!isLg ? (
        <button
          type="button"
          aria-label="Close navigation"
          onClick={onClose}
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 1000,
            border: 'none',
            padding: 0,
            margin: 0,
            background: open ? 'rgba(0,0,0,0.45)' : 'transparent',
            opacity: open ? 1 : 0,
            pointerEvents: open ? 'auto' : 'none',
            transition: 'opacity 0.2s ease',
          }}
        />
      ) : null}

      <View
        position={isLg ? 'relative' : 'fixed'}
        top={0}
        left={0}
        zIndex={isLg ? 0 : 1001}
        height="100%"
        minHeight="100vh"
        width={isLg ? (desktopCollapsed ? 'size-900' : 'size-3600') : 'size-3600'}
        maxWidth={isLg ? undefined : '85vw'}
        backgroundColor="gray-100"
        borderEndWidth="thin"
        borderColor="gray-200"
        UNSAFE_style={
          !isLg
            ? {
                transform: sidebarVisible ? 'translateX(0)' : 'translateX(-100%)',
                transition: 'transform 0.25s ease',
              }
            : undefined
        }
      >
        <View height="100%" padding={narrowRail ? 'size-100' : 'size-200'}>
          <Flex direction="column" height="100%" gap={narrowRail ? 'size-150' : 'size-200'} alignItems={narrowRail ? 'stretch' : undefined}>
            <Flex
              justifyContent={narrowRail ? 'center' : 'space-between'}
              alignItems="center"
              gap="size-100"
              width="100%"
            >
              <RouterLink
                to="/"
                style={{
                  textDecoration: 'none',
                  color: 'inherit',
                  display: narrowRail ? 'flex' : 'block',
                  justifyContent: narrowRail ? 'center' : undefined,
                  width: narrowRail ? '100%' : undefined,
                }}
              >
                <Flex alignItems="center" justifyContent={narrowRail ? 'center' : undefined} gap="size-150">
                  <View padding="size-100" borderRadius="medium" backgroundColor="blue-600">
                    <ProductIcon size={28} variant="glyph" style={{ color: 'var(--spectrum-white)' }} />
                  </View>
                  {!desktopCollapsed || !isLg ? (
                    <Flex direction="column" gap="size-50">
                      <Text UNSAFE_style={{ fontWeight: 700 }}>YouTube Copilot</Text>
                      <Text UNSAFE_style={{ fontSize: 12 }}>Enterprise workspace</Text>
                    </Flex>
                  ) : null}
                </Flex>
              </RouterLink>
              {!isLg ? (
                <ActionButton onPress={onClose} aria-label="Close navigation">
                  ✕
                </ActionButton>
              ) : null}
            </Flex>

            {(!desktopCollapsed || !isLg) && (
              <View
                padding="size-200"
                borderRadius="medium"
                borderWidth="thin"
                borderColor="gray-300"
                backgroundColor="gray-50"
              >
                <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em' }}>WORKSPACE</Text>
                <Text UNSAFE_style={{ fontSize: 13, marginTop: 8, lineHeight: 1.5 }}>
                  Summarize, learn, and ask questions in one shell.
                </Text>
              </View>
            )}

            <View flex={1} minHeight={0} width="100%" UNSAFE_style={{ overflowY: 'auto' }}>
              <Flex direction="column" gap={narrowRail ? 'size-100' : 'size-75'} alignItems="stretch">
                {navigationItems.map((item) => {
                  const Icon = item.icon
                  return (
                    <NavLink
                      key={item.id}
                      to={item.path}
                      end={item.path === '/dashboard'}
                      onClick={onClose}
                      style={{
                        textDecoration: 'none',
                        color: 'inherit',
                        display: 'block',
                        width: '100%',
                      }}
                    >
                      {({ isActive }) => (
                        <View
                          width="100%"
                          paddingY={narrowRail ? 'size-100' : 'size-150'}
                          paddingX={narrowRail ? 'size-65' : 'size-150'}
                          borderRadius="medium"
                          backgroundColor={isActive ? 'gray-75' : undefined}
                          borderStartWidth={isActive && !narrowRail ? 'thicker' : undefined}
                          borderStartColor={isActive && !narrowRail ? 'blue-600' : undefined}
                          borderWidth={isActive && narrowRail ? 'thin' : undefined}
                          borderColor={isActive && narrowRail ? 'blue-500' : undefined}
                        >
                          <Flex
                            alignItems={narrowRail ? 'center' : 'start'}
                            justifyContent={narrowRail ? 'center' : 'start'}
                            gap="size-150"
                          >
                            <View
                              padding="size-100"
                              borderRadius="small"
                              backgroundColor={isActive ? 'static-indigo-200' : 'gray-200'}
                              UNSAFE_style={{
                                color: isActive
                                  ? 'var(--spectrum-indigo-900)'
                                  : 'var(--spectrum-gray-700)',
                                flexShrink: 0,
                              }}
                            >
                              <Icon width={20} height={20} />
                            </View>
                            {(!desktopCollapsed || !isLg) && (
                              <Flex direction="column" gap="size-50" minWidth={0}>
                                <Text UNSAFE_style={{ fontWeight: 600, fontSize: 14 }}>{item.label}</Text>
                                <Text UNSAFE_style={{ fontSize: 12, opacity: 0.85 }}>{item.description}</Text>
                              </Flex>
                            )}
                          </Flex>
                        </View>
                      )}
                    </NavLink>
                  )
                })}
              </Flex>
            </View>

            {(!desktopCollapsed || !isLg) && (
              <View padding="size-200" borderRadius="medium" backgroundColor="gray-200">
                <Heading level={4} UNSAFE_style={{ fontSize: 11 }}>
                  Need help?
                </Heading>
                <Text UNSAFE_style={{ fontSize: 13, marginTop: 8 }}>
                  Use search in the header or open the assistant panel for route tips.
                </Text>
              </View>
            )}

            {isLg ? (
              <Flex justifyContent={narrowRail ? 'center' : 'stretch'} width="100%">
                <ActionButton
                  isQuiet={narrowRail}
                  width={narrowRail ? undefined : '100%'}
                  onPress={onToggleDesktopCollapsed}
                  aria-label={desktopCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
                >
                  {desktopCollapsed ? '↔' : 'Collapse'}
                </ActionButton>
              </Flex>
            ) : null}
          </Flex>
        </View>
      </View>
    </>
  )
}
