import React from 'react';
import PageTemplate from '@/components/common/PageTemplate';

const EventListPage: React.FC = () => {
  return (
    <PageTemplate
      title="Event List"
      description="View and analyze event list data from X-ray observations"
      category="Time Domain"
      status="coming-soon"
    />
  );
};

export default EventListPage;
