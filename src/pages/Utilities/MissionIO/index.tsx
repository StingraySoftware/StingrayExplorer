import React from 'react';
import PageTemplate from '@/components/common/PageTemplate';

const MissionIOPage: React.FC = () => {
  return (
    <PageTemplate
      title="Mission Specific I/O"
      description="I/O adapters for specific X-ray missions (RXTE, XMM, Chandra, etc.)"
      category="Utilities"
      status="coming-soon"
    />
  );
};

export default MissionIOPage;
