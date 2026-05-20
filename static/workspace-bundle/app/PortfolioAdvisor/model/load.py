from strands.models.bedrock import BedrockModel


def load_model() -> BedrockModel:
    return BedrockModel(model_id="us.anthropic.claude-sonnet-4-6")
