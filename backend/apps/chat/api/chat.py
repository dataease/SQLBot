from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import select
from apps.chat.schemas.chat_base_schema import LLMConfig
from apps.chat.schemas.chat_schema import ChatQuestion
from apps.chat.schemas.llm import AgentService, LLMService
from apps.datasource.models.datasource import CoreDatasource
from apps.system.models.system_model import AiModelDetail
from common.core.deps import SessionDep
from sse_starlette.sse import EventSourceResponse
import json
import asyncio

router = APIRouter(tags=["Data Q&A"], prefix="/chat")


@router.post("/question")
async def stream_sql(session: SessionDep, requestQuestion: ChatQuestion):
    """Stream SQL analysis results
    
    Args:
        session: Database session
        requestQuestion: User question model
        
    Returns:
        Streaming response with analysis results
    """
    question = requestQuestion.question
    
    # Get available AI model
    aimodel = session.exec(select(AiModelDetail).where(
        AiModelDetail.status == True, 
        AiModelDetail.api_key.is_not(None)
    )).first()
    
    # Get available datasource
    ds = session.exec(select(CoreDatasource).where(
        CoreDatasource.status == 'Success'
    )).first()

    if not aimodel:
        raise HTTPException(
            status_code=400,
            detail="No available AI model configuration found"
        )
        
    if not ds:
        raise HTTPException(
            status_code=400,
            detail="No available datasource configuration found"
        )
    
    # Use Tongyi Qianwen
    tongyi_config = LLMConfig(
        model_type="openai",
        model_name=aimodel.name,
        api_key=aimodel.api_key,
        api_base_url=aimodel.endpoint,
        additional_params={"temperature": aimodel.temperature}
    )
    # llm_service = LLMService(tongyi_config)
    llm_service = AgentService(tongyi_config, ds)

    # Use Custom VLLM model
    """ vllm_config = LLMConfig(
        model_type="vllm",
        model_name="your-model-path",
        additional_params={
            "max_new_tokens": 200,
            "temperature": 0.3
        }
    )
    vllm_service = LLMService(vllm_config) """
    """ result = llm_service.generate_sql(question)
    return result """
    
    async def event_generator():
        try:
            async for chunk in llm_service.async_generate(question):
                data = json.loads(chunk.replace('data: ', ''))
                
                if data['type'] in ['final', 'tool_result']:
                    content = data['content']
                    for char in content:
                        yield f"data: {json.dumps({'type': 'char', 'content': char})}\n\n"
                        await asyncio.sleep(0.05) 
                    
                    if 'html' in data:
                        yield f"data: {json.dumps({'type': 'html', 'content': data['html']})}\n\n"
                else:
                    yield chunk
                    
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
    
    #return EventSourceResponse(event_generator(), headers={"Content-Type": "text/event-stream"})
    return StreamingResponse(event_generator(), media_type="text/event-stream")