import enum


class EnvironmentChoices(enum.StrEnum):
    """
    Environment choices for the application.
    
    PRODUCTION: Production environment
    LOCAL: Local environment
    DEVELOPMENT: Development environment
    QA: Quality Assurance environment
    """

    PRODUCTION = "production"
    LOCAL = "local"
    DEVELOPMENT = "development"
    QA = "qa"