import type { RoleplayBootstrap } from './types';

const defaultBootstrap: RoleplayBootstrap = {
  apiBaseUrl: '/api/roleplay',
  wsBasePath: '/ws/roleplay',
  currentUser: {
    displayName: 'Player1',
    isAuthenticated: true,
  },
  defaultNickname: 'Player1',
};

export function getRoleplayBootstrap(): RoleplayBootstrap {
  if (typeof document === 'undefined') {
    return defaultBootstrap;
  }

  const script = document.getElementById('roleplay-bootstrap');
  if (!script?.textContent) {
    return defaultBootstrap;
  }

  try {
    const parsed = JSON.parse(script.textContent) as Partial<RoleplayBootstrap>;
    return {
      ...defaultBootstrap,
      ...parsed,
      currentUser: {
        ...defaultBootstrap.currentUser,
        ...parsed.currentUser,
      },
    };
  } catch (_error) {
    return defaultBootstrap;
  }
}
