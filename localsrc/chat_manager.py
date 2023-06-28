class ChatManager:
    def __init__(self, user_id, channel_id, prompt_key):
        self._user_id = user_id
        self._channel_id = channel_id
        self._prompt_key = prompt_key

    # Getter for channel_id
    @property
    def channel_id(self):
        return self._channel_id

    # Setter for channel_id
    @channel_id.setter
    def channel_id(self, value):
        self._channel_id = value

    # Getter for user_id
    @property
    def user_id(self):
        return self._user_id

    # Setter for user_id
    @user_id.setter
    def user_id(self, value):
        self._user_id = value

    # Getter for thread_ts
    @property
    def thread_ts(self):
        return self._thread_ts

    # Setter for thread_ts
    @thread_ts.setter
    def thread_ts(self, value):
        self._thread_ts = value

    # Getter for prompt_key
    @property
    def prompt_key(self):
        return self._prompt_key

    # Setter for prompt_key
    @prompt_key.setter
    def prompt_key(self, value):
        self._prompt_key = value
