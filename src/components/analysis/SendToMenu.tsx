import React from 'react';
import { useNavigate } from 'react-router';
import { Button, ListItemText, Menu, MenuItem } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import { setWorkspaceFields } from '@/api/workspaceSession';
import { FUTURE_SEND_TARGETS, SendAction, UnavailableSendAction } from '@/utils/sendTo';

interface SendToMenuProps {
  actions: SendAction[];
  /** Destinations that do not apply to this result, shown disabled with a reason. */
  unavailable?: UnavailableSendAction[];
}

/** Open another page with this result's inputs already filled in. */
const SendToMenu: React.FC<SendToMenuProps> = ({ actions, unavailable = [] }) => {
  const navigate = useNavigate();
  const [anchor, setAnchor] = React.useState<HTMLElement | null>(null);
  const send = (action: SendAction): void => {
    setWorkspaceFields(action.fields);
    setAnchor(null);
    navigate(action.route);
  };
  return (
    <>
      <Button
        size="small"
        variant="outlined"
        startIcon={<SendIcon fontSize="small" />}
        onClick={(event) => setAnchor(event.currentTarget)}
      >
        Send to
      </Button>
      <Menu anchorEl={anchor} open={anchor !== null} onClose={() => setAnchor(null)}>
        {actions.map((action) => (
          <MenuItem key={action.label} onClick={() => send(action)}>
            {action.label}
          </MenuItem>
        ))}
        {[...unavailable, ...FUTURE_SEND_TARGETS].map((target) => (
          <MenuItem key={target.label} disabled>
            <ListItemText primary={target.label} secondary={target.reason} />
          </MenuItem>
        ))}
      </Menu>
    </>
  );
};

export default SendToMenu;
