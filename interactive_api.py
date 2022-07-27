import logging
from functools import wraps

import torch
from fastapi import FastAPI

from inference.inference_core import InferenceCore
from inference.interact.fbrs_controller import FBRSController
from inference.interact.s2m.s2m_network import deeplabv3plus_resnet50 as S2M
from inference.interact.s2m_controller import S2MController
from model.network import XMem


# https://stackoverflow.com/questions/23983150/how-can-i-log-a-functions-arguments-in-a-reusable-way-in-python
def arg_logger(func):
    @wraps(func)
    def new_func(*args, **kwargs):
        saved_args = locals()
        try:
            return func(*args, **kwargs)
        except:
            logging.exception("Oh no! My args were: " + str(saved_args))
            raise

    return new_func


app = FastAPI()


processor = None
s2m_model = None
s2m_controller = None
fbrs_controller = None

s2m_model_path = "saves/s2m.pth"
fbrs_model_path = "saves/fbrs.pth"
network_path = "saves/XMem.pth"
# get attribute from a.b.c


def get_attr(obj, attr_str):
    attr_list = attr_str.split(".")
    for attr in attr_list:
        obj = getattr(obj, attr)
    return obj


@arg_logger
@app.post("/api/network/")
def core_interact(request: dict):
    global processor
    if "var_name" in request:
        try:
            result = get_attr(processor, request["var_name"])
            return {"value": result, "code": 0}
        except:
            return {"value": "error", "code": -1}

    assert "func_name" in request
    request.setdefault("args", {})
    if request.get("args", None) is None:
        request["args"] = {}
    if request["func_name"] == "__init__":
        if processor is None:
            print("loading InferenceCore")
            network = XMem(model_path=network_path, **request.get("args", {}))
            processor = InferenceCore(network=network, **request.get("args", {}))
            print("InferenceCore loaded")
            return {"code": 0, "result": None}

    else:
        result = processor.__getattribute__(request["func_name"])(
            **request.get("args", {})
        )
        return {"code": 0, "result": result}


@arg_logger
@app.post("/api/s2m/")
def s2m_interact(request: dict):
    global s2m_controller
    assert "func_name" in request
    request.setdefault("args", {})
    if request.get("args", None) is None:
        request["args"] = {}
    if request["func_name"] == "__init__":
        if s2m_controller is None:
            print("loading network")
            if s2m_model_path is not None:
                s2m_saved = torch.load(s2m_model_path)
                s2m_model = S2M().cuda().eval()
                s2m_model.load_state_dict(s2m_saved)
            else:
                s2m_model = None
            s2m_controller = S2MController(s2m_net=s2m_model, **request.get("args", {}))
            print("network loaded")
            return {"code": 0, "result": None}

    else:
        result = s2m_controller.__getattribute__(request["func_name"])(
            **request.get("args", {})
        )
        return {"code": 0, "result": result}


@arg_logger
@app.post("/api/fbrs/")
def fbrs_interact(request: dict):
    global fbrs_controller
    assert "func_name" in request
    request.setdefault("args", {})
    if request.get("args", None) is None:
        request["args"] = {}
    if request["func_name"] == "__init__":
        if fbrs_controller is None:
            print("loading network")
            fbrs_controller = FBRSController(checkpoint_path=fbrs_model_path)
            print("network loaded")
            return {"code": 0, "result": None}

    else:
        result = fbrs_controller.__getattribute__(request["func_name"])(
            **request.get("args", {})
        )
        return {"code": 0, "result": result}
