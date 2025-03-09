import { render, screen } from '@testing-library/react';
import NegativeConversationPage from './page';
import DialogueChatConfigurable from '../components/DialogueChatConfigurable';
import prompts from '../utils/prompts.json';

// Mock the DialogueChatConfigurable component
jest.mock('../components/DialogueChatConfigurable', () => {
  return jest.fn(() => <div data-testid="mocked-dialogue-chat">Mocked DialogueChat</div>);
});

// Mock the prompts.json
jest.mock('../utils/prompts.json', () => ({
  negative: {
    title: "Mocked Negative Title",
    description: "Mocked Negative Description",
    articlePrompt: "Mocked Article Prompt",
    mode: "supportive"
  },
  positive: {
    title: "Mocked Positive Title",
    description: "Mocked Positive Description",
    articlePrompt: "Mocked Positive Article Prompt",
    mode: "critical"
  }
}));

describe('NegativeConversationPage', () => {
  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
  });

  it('renders DialogueChatConfigurable with correct props', () => {
    render(<NegativeConversationPage />);
    
    // Verify DialogueChatConfigurable was called with the correct props
    expect(DialogueChatConfigurable).toHaveBeenCalledWith(
      {
        websocketUrl: 'wss://21b5-16-170-227-168.ngrok-free.app/ws/conversation',
        promptConfig: prompts.negative
      },
      expect.anything()
    );
    
    // Verify the component renders
    expect(screen.getByTestId('mocked-dialogue-chat')).toBeInTheDocument();
  });
});