
class ChatManager:

    def __init__(self, user_id, channel_id, prompt_key):
        self._user_id = user_id
        # Objects of this class hold a dictionary of Slack Channels
        # which contain a dictionary of Slack Threads that have 
        # GPT4 system prompts associated them.
        self._channels = {channel_id: {}}
        self._prompt_key = prompt_key

    # Getter for user_id
    @property
    def user_id(self):
        return self._user_id

    # Setter for user_id
    @user_id.setter
    def user_id(self, value):
        self._user_id = value

    # Getter for _channels
    @property
    def channels(self):
        return self._channels      
    
    # Method to add a new channel
    def add_channel(self, channel_id):
        if channel_id not in self._channels:
            self._channels[channel_id] = {}   

    # Getter for a specific channel
    def get_channel(self, channel_id):
        return self._channels.get(channel_id, None)  

    # Method to add a new thread to a channel
    def add_thread_to_channel(self, channel_id, thread_ts, prompt_key):
        # Check if the channel exists, if not, add it.
        if channel_id not in self._channels:
            self._channels[channel_id] = {}

        # Add the new thread to the channel
        self._channels[channel_id][thread_ts] = prompt_key

    # Getter for prompt_key
    @property
    def prompt_key(self):
        return self._prompt_key

    # Setter for prompt_key
    @prompt_key.setter
    def prompt_key(self, value):
        self._prompt_key = value

    # Print object as string
    def __str__(self):
        return f"Object of ChatManager - user_id: {self._user_id}, channels: {self._channels}, prompt_key: {self._prompt_key}"