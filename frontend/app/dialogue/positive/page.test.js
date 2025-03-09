import { render, screen } from '@testing-library/react';
import PositiveConversationPage from './page';
import DialogueChatConfigurable from '../../components/DialogueChatConfigurable';
import prompts from '../../utils/prompts.json';
import config from '../../utils/config';

// Mock the DialogueChatConfigurable component
jest.mock('../../components/DialogueChatConfigurable', () => {
  return jest.fn(() => <div data-testid="mocked-dialogue-chat">Mocked DialogueChat</div>);
});

// Mock the prompts.json
jest.mock('../../utils/prompts.json', () => ({
  positive: {
    title: "Apollolytics Dialogue",
    articlePrompt: "Enter a propagandistic article text:",
    mode: "critical"
  }
}));

// Mock the config
jest.mock('../../utils/config', () => ({
  getWebsocketUrl: jest.fn(() => 'ws://mocked-url/ws/conversation')
}));

describe('PositiveConversationPage', () => {
  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
  });

  it('renders DialogueChatConfigurable with correct props', () => {
    render(<PositiveConversationPage />);
    
    // Verify config.getWebsocketUrl was called
    expect(config.getWebsocketUrl).toHaveBeenCalled();
    
    // Verify DialogueChatConfigurable was called with the correct props
    expect(DialogueChatConfigurable).toHaveBeenCalledWith(
      {
        websocketUrl: 'ws://mocked-url/ws/conversation',
        promptConfig: prompts.positive
      },
      expect.anything()
    );
    
    // Verify the component renders
    expect(screen.getByTestId('mocked-dialogue-chat')).toBeInTheDocument();
  });
});