import json

from servc.svc.com.bus.rabbitmq import BusRabbitMQ
from servc.svc.com.cache.redis import CacheRedis
from servc.svc.com.worker.types import RESOLVER_CONTEXT
from servc.svc.config import Config


def get_context() -> RESOLVER_CONTEXT:
    config = Config()
    bus = BusRabbitMQ(config.get("conf.bus"))
    cache = CacheRedis(config.get("conf.cache"))

    return {
        "bus": bus,
        "cache": cache,
        "middlewares": [],
        "config": config,
    }


def get_route_message(route: str):
    context = get_context()
    bus = context["bus"]
    cache = context["cache"]
    bus.connect()
    channel = bus._conn.channel()

    queue = channel.queue_declare(
        queue=route,
        passive=True,
        durable=True,
        exclusive=False,
        auto_delete=False,
    )
    count: int = queue.method.message_count
    body = None

    if count:
        _m, _h, body = channel.basic_get(route)
    if body:
        body = json.loads(body.decode("utf-8"))
        if "argumentId" in body:
            body["argument"] = cache.getKey(body["argumentId"])

    channel.close()
    bus.close()
    cache.close()
    return body, count
