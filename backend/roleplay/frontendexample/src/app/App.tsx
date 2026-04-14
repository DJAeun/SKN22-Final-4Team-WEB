import { useState } from 'react';
import { getRoleplayBootstrap } from './bootstrap';
import { MainGamePage } from './components/MainGamePage';
import { NDAEntrancePage } from './components/NDAEntrancePage';

const NDA_KEY = 'hari_nda_accepted';

export default function App() {
  const bootstrap = getRoleplayBootstrap();
  const [hasAcceptedNDA, setHasAcceptedNDA] = useState(
    () => localStorage.getItem(NDA_KEY) === 'true'
  );

  const handleAccept = () => {
    localStorage.setItem(NDA_KEY, 'true');
    setHasAcceptedNDA(true);
  };

  return (
    <div className="size-full">
      {!hasAcceptedNDA ? (
        <NDAEntrancePage
          defaultNickname={bootstrap.defaultNickname}
          onAccept={handleAccept}
        />
      ) : (
        <MainGamePage bootstrap={bootstrap} onBack={() => setHasAcceptedNDA(false)} />
      )}
    </div>
  );
}
