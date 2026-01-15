"""
Dialer service for initiating and managing calls via FreeSWITCH ESL
"""

import asyncio
from typing import Optional
import uuid

import structlog

logger = structlog.get_logger(__name__)

# FreeSWITCH ESL connection settings
ESL_HOST = "127.0.0.1"
ESL_PORT = 8021
ESL_PASSWORD = "ClueCon"

# SIP trunk settings (from dialplan)
TECH_PREFIX = "1290#"
GATEWAY = "ligai-trunk"


async def _send_esl_command(command: str) -> tuple[bool, str]:
    """
    Send a command to FreeSWITCH via Event Socket Library.

    Returns:
        Tuple of (success, response_text)
    """
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ESL_HOST, ESL_PORT),
            timeout=5.0
        )

        # Read banner
        await reader.readuntil(b"\n\n")

        # Authenticate
        writer.write(f"auth {ESL_PASSWORD}\n\n".encode())
        await writer.drain()
        auth_response = await reader.readuntil(b"\n\n")

        if b"+OK" not in auth_response:
            logger.error("ESL authentication failed")
            writer.close()
            await writer.wait_closed()
            return False, "Authentication failed"

        # Send command
        writer.write(f"{command}\n\n".encode())
        await writer.drain()

        # Read response header
        response = await asyncio.wait_for(
            reader.readuntil(b"\n\n"),
            timeout=10.0
        )

        response_text = response.decode("utf-8", errors="ignore")

        # Check if there's a Content-Length header and read the body
        if "Content-Length:" in response_text:
            try:
                for line in response_text.split("\n"):
                    if line.startswith("Content-Length:"):
                        content_length = int(line.split(":")[1].strip())
                        if content_length > 0:
                            body = await asyncio.wait_for(
                                reader.read(content_length),
                                timeout=5.0
                            )
                            response_text += body.decode("utf-8", errors="ignore")
                        break
            except Exception:
                pass

        writer.close()
        await writer.wait_closed()

        success = "+OK" in response_text and "-ERR" not in response_text

        return success, response_text

    except asyncio.TimeoutError:
        logger.error("ESL command timeout", command=command)
        return False, "Timeout"
    except Exception as e:
        logger.exception("ESL command failed", command=command, error=str(e))
        return False, str(e)


async def initiate_call(
    number: str,
    prompt_config: Optional[dict] = None
) -> Optional[str]:
    """
    Initiate an outbound call to a phone number.

    Args:
        number: Phone number to call (10-11 digits)
        prompt_config: Optional prompt configuration dict

    Returns:
        call_id if successful, None otherwise
    """
    # Generate unique call ID
    call_id = f"call-{int(asyncio.get_event_loop().time())}-{uuid.uuid4().hex[:8]}"

    # Clean number (remove non-digits)
    clean_number = "".join(filter(str.isdigit, number))

    # Accept 10-11 digits (local) or 12-13 digits (with country code 55)
    if len(clean_number) < 10 or len(clean_number) > 13:
        logger.error("Invalid phone number", number=number)
        return None

    # Add country code 55 if not present (10-11 digits = local number)
    if len(clean_number) <= 11:
        clean_number = "55" + clean_number

    # Build originate command with api_on_answer to connect audio_fork
    # The metadata JSON will be passed to the WebSocket handler
    metadata = f'{{\\"uuid\\":\\"{call_id}\\"}}'

    originate_cmd = (
        f"bgapi originate "
        f"{{origination_uuid={call_id},"
        f"ignore_early_media=true,"
        f"api_on_answer='uuid_audio_fork {call_id} start ws://127.0.0.1:8000/ws/{call_id} mono 8000 {metadata}'}}"
        f"sofia/gateway/{GATEWAY}/{TECH_PREFIX}{clean_number} &park"
    )

    logger.info("Initiating call", call_id=call_id, number=clean_number)

    success, response = await _send_esl_command(originate_cmd)

    if success:
        logger.info("Call initiated successfully", call_id=call_id)

        # Store prompt config for this call if provided
        if prompt_config:
            from state import pending_call_configs
            pending_call_configs[call_id] = prompt_config

        # Store the called number for this call
        from state import pending_call_numbers
        pending_call_numbers[call_id] = clean_number

        return call_id
    else:
        logger.error("Failed to initiate call", call_id=call_id, response=response)
        return None


async def hangup_call(freeswitch_uuid: str) -> bool:
    """
    Hang up a call by its FreeSWITCH UUID.

    Args:
        freeswitch_uuid: The FreeSWITCH channel UUID

    Returns:
        True if successful, False otherwise
    """
    command = f"api uuid_kill {freeswitch_uuid}"

    logger.info("Hanging up call", uuid=freeswitch_uuid)

    success, response = await _send_esl_command(command)

    if success:
        logger.info("Call hung up successfully", uuid=freeswitch_uuid)
    else:
        logger.error("Failed to hang up call", uuid=freeswitch_uuid, response=response)

    return success


async def get_channel_status(freeswitch_uuid: str) -> Optional[dict]:
    """
    Get the status of a FreeSWITCH channel.

    Returns:
        Channel info dict or None if not found
    """
    command = f"api uuid_exists {freeswitch_uuid}"

    success, response = await _send_esl_command(command)

    if success and "true" in response.lower():
        return {"uuid": freeswitch_uuid, "active": True}
    return None
