class InvalidRequest(Exception):
    def __init__(self, request, message=None):
        self.msg = f'Invalid request {request}. ' + message
        super().__init__(self.msg)


class AlreadyProcessed(Exception):
    def __init__(self, thing):
        self.msg = f'{thing} was already processed.'
        super().__init__(self.msg)


class CurrentlyProcessing(Exception):
    def __init__(self, thing):
        self.msg = f'{thing} is currently being processed.'
        super().__init__(self.msg)


class CommentingFailed(Exception):
    def __init__(self, thing):
        self.msg = f"Couldn't comment to {thing}."
        super().__init__(self.msg)


class UploadFailed(Exception):
    def __init__(self, thing):
        self.msg = f"Couldn't upload {thing}."
        super().__init__(self.msg)