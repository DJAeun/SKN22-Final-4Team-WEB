export interface RoleplayBootstrap {
  apiBaseUrl: string;
  wsBasePath: string;
  currentUser: {
    displayName: string;
    isAuthenticated: boolean;
  };
  defaultNickname: string;
}

export interface SessionSummary {
  id: string;
  user_nickname: string;
  status_window_enabled: boolean;
  total_tokens: number;
  stress: number;
  crack_stage: number;
  current_thought: string;
  current_date: string;
  current_time: string;
  current_location: string;
  created_at: string;
  updated_at: string;
}

export interface StatusSnapshot {
  date: string;
  time: string;
  location: string;
  stress?: number | null;
  crack_stage?: number | null;
  thought?: string;
}

export interface ChatHistoryItem {
  id: number;
  session: string;
  role: string;
  content: string;
  status_snapshot?: StatusSnapshot | null;
  image_command?: string | null;
  image_url?: string | null;
  created_at: string;
}

export interface GameMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  storyContext: string;
  sourceRole?: string;
  imageCommand?: string | null;
  imageUrl?: string | null;
}
