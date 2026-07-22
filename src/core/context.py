class ContextResolver:
    def __init__(self, memory):
        self.memory = memory
        self.active_store = None

    def resolve_login(self, user_id):
        """
        Called when user logs in.
        Returns:
        - ('READY', context_string): If 1 store found.
        - ('AMBIGUOUS', store_list): If multiple stores found.
        - ('EMPTY', None): If no stores found.
        """
        stores = self.memory.get_user_stores(user_id)

        if not stores:
            return "EMPTY", None

        if len(stores) == 1:
            self.active_store = stores[0]
            context = self._build_context_string(stores[0])
            return "READY", context

        # If multiple stores, we need the user to pick one
        return "AMBIGUOUS", stores

    def set_active_store(self, store):
        self.active_store = store
        return self._build_context_string(store)

    def _build_context_string(self, store):
        return f'''
        ACTIVE STORE CONTEXT (FROM DATABASE):
        - Store Name: {store['name']}
        - Industry: {store['industry']}
        - Location: {store['location']}
        - ID: {store['id']}
        '''
