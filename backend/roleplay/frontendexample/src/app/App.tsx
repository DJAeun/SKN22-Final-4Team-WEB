import { useState } from 'react';
import { getRoleplayBootstrap } from './bootstrap';
import { MainGamePage } from './components/MainGamePage';
import { NDAEntrancePage } from './components/NDAEntrancePage';

export default function App() {
  const bootstrap = getRoleplayBootstrap();
  const [hasAcceptedNDA, setHasAcceptedNDA] = useState(false);

  return (
    <div className="size-full">
      {!hasAcceptedNDA ? (
        <NDAEntrancePage
          defaultNickname={bootstrap.defaultNickname}
          onAccept={() => setHasAcceptedNDA(true)}
        />
      ) : (
        <MainGamePage bootstrap={bootstrap} />
      )}
    </div>
  );
}
