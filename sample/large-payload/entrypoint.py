class JobEntrypoint:

    def perform(self, text: str) -> int:
        return len(text)

    def docs_input_example(self) -> dict:
        """Return example input values for this model"""
        return {'text': 'very long text'}
