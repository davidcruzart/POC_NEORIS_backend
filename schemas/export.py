from pydantic import BaseModel


class ExportMetadataResponse(BaseModel):
    filename: str
    output_format: str