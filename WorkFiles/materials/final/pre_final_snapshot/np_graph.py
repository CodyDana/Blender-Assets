"""A small expression-graph builder over unreal.MaterialEditingLibrary (runs inside Unreal only).

Every node is created through ``Graph``; operands may be ``Out`` handles, Python floats (a shared Constant node) or
3/4-tuples (a Constant3Vector / Constant4Vector). Every connection is checked: ``connect_material_expressions`` returns
False on a bad pin name, and the builder raises with the node's real input names instead of leaving a silent gap.

Measured on UE 5.8.3 (WorkFiles/materials/build/probe_api.json): pin names are
    Add/Subtract/Multiply/Divide/Max/Min/DotProduct/AppendVector  "A", "B"
    Power "Base", "Exp";  LinearInterpolate "A", "B", "Alpha";  If "A", "B", "A > B", "A == B", "A < B"
    Logarithm2 "X";  Normalize "VectorInput";  TextureSample "UVs", "Tex";  StaticSwitchParameter "True", "False"
    single-input nodes (Saturate, Abs, Ceil, OneMinus, ComponentMask, Exponential, FunctionOutput) ""
"""
from __future__ import annotations

import unreal

MEL = unreal.MaterialEditingLibrary

GROUP_SORT = {}


class Out:
    """One output of one expression node."""
    __slots__ = ("g", "node", "out")

    def __init__(self, g: "Graph", node, out: str = ""):
        self.g, self.node, self.out = g, node, out

    def __repr__(self):
        return f"<{self.node.get_name()}:{self.out or '-'}>"

    # component access
    @property
    def r(self):
        return self.g.mask(self, "r")

    @property
    def gch(self):
        return self.g.mask(self, "g")

    @property
    def b(self):
        return self.g.mask(self, "b")

    @property
    def a(self):
        return self.g.mask(self, "a")

    @property
    def rgb(self):
        return self.g.mask(self, "rgb")


class Tex:
    """The named outputs of a texture sample node."""

    def __init__(self, g, node):
        self.g, self.node = g, node
        self.rgb = Out(g, node, "RGB")
        self.r = Out(g, node, "R")
        self.gch = Out(g, node, "G")
        self.b = Out(g, node, "B")
        self.a = Out(g, node, "A")
        self.rgba = Out(g, node, "RGBA")


class Call:
    """A MaterialFunctionCall: outputs by the function's output names."""

    def __init__(self, g, node):
        self.g, self.node = g, node

    def __getitem__(self, name):
        return Out(self.g, self.node, name)


class Graph:
    def __init__(self, owner, is_function: bool = False):
        self.owner = owner
        self.fn = is_function
        self.count = 0
        self._consts = {}
        self.params = []

    # ------------------------------------------------------------------ nodes
    def new(self, cls, **props):
        self.count += 1
        x, y = -400 - 220 * (self.count // 25), 180 * (self.count % 25)
        create = MEL.create_material_expression_in_function if self.fn else MEL.create_material_expression
        node = create(self.owner, cls, x, y)
        if node is None:
            raise RuntimeError(f"could not create {cls.__name__} in {self.owner.get_name()}")
        for k, v in props.items():
            node.set_editor_property(k, v)
        return node

    def _as_out(self, v) -> Out:
        if isinstance(v, (Out,)):
            return v
        if isinstance(v, (int, float)):
            return self.const(float(v))
        if isinstance(v, (tuple, list)) and len(v) in (3, 4):
            return self.const_vec(tuple(float(x) for x in v))
        raise TypeError(f"not a graph value: {v!r}")

    def link(self, src, node, pin: str):
        src = self._as_out(src)
        ok = MEL.connect_material_expressions(src.node, src.out, node, pin)
        if not ok:
            names = [str(n) for n in MEL.get_material_expression_input_names(node)]
            outs = [str(n) for n in MEL.get_material_expression_output_names(src.node)] if hasattr(MEL, "get_material_expression_output_names") else "?"
            raise RuntimeError(f"connect failed: {src.node.get_name()}.{src.out!r} -> {node.get_name()}.{pin!r} "
                               f"(inputs {names}, source outputs {outs})")

    def op(self, cls, pins: dict, **props) -> Out:
        node = self.new(cls, **props)
        for pin, src in pins.items():
            if src is not None:
                self.link(src, node, pin)
        return Out(self, node, "")

    # ------------------------------------------------------------------ constants
    def const(self, v: float) -> Out:
        key = ("s", v)
        if key not in self._consts:
            self._consts[key] = Out(self, self.new(unreal.MaterialExpressionConstant, r=v))
        return self._consts[key]

    def const_vec(self, v: tuple) -> Out:
        key = ("v", v)
        if key not in self._consts:
            if len(v) == 3:
                node = self.new(unreal.MaterialExpressionConstant3Vector, constant=unreal.LinearColor(v[0], v[1], v[2], 1.0))
            else:
                node = self.new(unreal.MaterialExpressionConstant4Vector, constant=unreal.LinearColor(*v))
            self._consts[key] = Out(self, node)
        return self._consts[key]

    # ------------------------------------------------------------------ math
    def add(self, a, b):
        return self.op(unreal.MaterialExpressionAdd, {"A": a, "B": b})

    def sub(self, a, b):
        return self.op(unreal.MaterialExpressionSubtract, {"A": a, "B": b})

    def mul(self, a, b):
        return self.op(unreal.MaterialExpressionMultiply, {"A": a, "B": b})

    def div(self, a, b):
        return self.op(unreal.MaterialExpressionDivide, {"A": a, "B": b})

    def max(self, a, b):
        return self.op(unreal.MaterialExpressionMax, {"A": a, "B": b})

    def min(self, a, b):
        return self.op(unreal.MaterialExpressionMin, {"A": a, "B": b})

    def pow(self, base, exp):
        return self.op(unreal.MaterialExpressionPower, {"Base": base, "Exp": exp})

    def lerp(self, a, b, alpha):
        return self.op(unreal.MaterialExpressionLinearInterpolate, {"A": a, "B": b, "Alpha": alpha})

    def dot(self, a, b):
        return self.op(unreal.MaterialExpressionDotProduct, {"A": a, "B": b})

    def append(self, a, b):
        return self.op(unreal.MaterialExpressionAppendVector, {"A": a, "B": b})

    def sat(self, x):
        return self.op(unreal.MaterialExpressionSaturate, {"": x})

    def abs(self, x):
        return self.op(unreal.MaterialExpressionAbs, {"": x})

    def ceil(self, x):
        return self.op(unreal.MaterialExpressionCeil, {"": x})

    def one_minus(self, x):
        return self.op(unreal.MaterialExpressionOneMinus, {"": x})

    def exp(self, x):
        return self.op(unreal.MaterialExpressionExponential, {"": x})

    def log2(self, x):
        return self.op(unreal.MaterialExpressionLogarithm2, {"X": x})

    def normalize(self, v):
        return self.op(unreal.MaterialExpressionNormalize, {"VectorInput": v})

    def mask(self, x, chans: str):
        return self.op(unreal.MaterialExpressionComponentMask, {"": x},
                       r="r" in chans, g="g" in chans, b="b" in chans, a="a" in chans)

    def if_(self, a, b, gt, eq, lt):
        """A > B ? gt : (A == B ? eq : lt)."""
        return self.op(unreal.MaterialExpressionIf, {"A": a, "B": b, "A > B": gt, "A == B": eq, "A < B": lt})

    def max3(self, v):
        """max(v.r, v.g, v.b)."""
        return self.max(self.max(self.mask(v, "r"), self.mask(v, "g")), self.mask(v, "b"))

    def texcoord(self, index=0):
        return Out(self, self.new(unreal.MaterialExpressionTextureCoordinate, coordinate_index=index))

    # ------------------------------------------------------------------ parameters
    def _param_common(self, node, name, group, sort, desc):
        node.set_editor_property("parameter_name", name)
        node.set_editor_property("group", group)
        node.set_editor_property("sort_priority", int(sort))
        if desc:
            node.set_editor_property("desc", desc)
        self.params.append(name)

    def scalar(self, name, default, group, sort, desc="", lo=None, hi=None) -> Out:
        node = self.new(unreal.MaterialExpressionScalarParameter)
        self._param_common(node, name, group, sort, desc)
        node.set_editor_property("default_value", float(default))
        if lo is not None and hi is not None:
            node.set_editor_property("slider_min", float(lo))
            node.set_editor_property("slider_max", float(hi))
        return Out(self, node, "")

    def vector(self, name, rgba, group, sort, desc="") -> Out:
        node = self.new(unreal.MaterialExpressionVectorParameter)
        self._param_common(node, name, group, sort, desc)
        rgba = list(rgba) + [1.0] * (4 - len(rgba))
        node.set_editor_property("default_value", unreal.LinearColor(*[float(x) for x in rgba[:4]]))
        return Out(self, node, "RGB")

    @staticmethod
    def rgba(vec_out: "Out") -> "Out":
        """The float4 output of a VectorParameter handle (its default handle is the float3 'RGB')."""
        return Out(vec_out.g, vec_out.node, "RGBA")

    def texture(self, name, texture, sampler, group, sort, desc="", uv=None) -> Tex:
        node = self.new(unreal.MaterialExpressionTextureSampleParameter2D)
        self._param_common(node, name, group, sort, desc)
        node.set_editor_property("texture", texture)
        node.set_editor_property("sampler_type", sampler)
        if uv is not None:
            self.link(uv, node, "UVs")
        return Tex(self, node)

    def texture_object(self, name, texture, sampler, group, sort, desc="") -> Out:
        node = self.new(unreal.MaterialExpressionTextureObjectParameter)
        self._param_common(node, name, group, sort, desc)
        node.set_editor_property("texture", texture)
        node.set_editor_property("sampler_type", sampler)
        return Out(self, node, "")

    def sample(self, tex_object, uv, sampler) -> Tex:
        """TextureSample of a Texture2D object input (used inside functions)."""
        node = self.new(unreal.MaterialExpressionTextureSample)
        node.set_editor_property("sampler_type", sampler)
        self.link(tex_object, node, "Tex")
        self.link(uv, node, "UVs")
        return Tex(self, node)

    def switch(self, name, default, group, sort, desc, when_true, when_false) -> Out:
        node = self.new(unreal.MaterialExpressionStaticSwitchParameter)
        self._param_common(node, name, group, sort, desc)
        node.set_editor_property("default_value", bool(default))
        self.link(when_true, node, "True")
        self.link(when_false, node, "False")
        return Out(self, node, "")

    def shading_model(self, msm) -> Out:
        return Out(self, self.new(unreal.MaterialExpressionShadingModel, shading_model=msm))

    # ------------------------------------------------------------------ functions
    def fn_input(self, name, input_type, sort, desc="", preview=None) -> Out:
        node = self.new(unreal.MaterialExpressionFunctionInput)
        node.set_editor_property("input_name", name)
        node.set_editor_property("input_type", input_type)
        node.set_editor_property("sort_priority", int(sort))
        if desc:
            node.set_editor_property("description", desc)
        if preview is not None:
            self.link(preview, node, "Preview")
        return Out(self, node, "")

    def fn_output(self, name, sort, src, desc=""):
        node = self.new(unreal.MaterialExpressionFunctionOutput)
        node.set_editor_property("output_name", name)
        node.set_editor_property("sort_priority", int(sort))
        if desc:
            node.set_editor_property("description", desc)
        self.link(src, node, "")
        return node

    def call(self, mf, inputs: dict) -> Call:
        node = self.new(unreal.MaterialExpressionMaterialFunctionCall)
        if hasattr(node, "set_material_function"):
            node.set_material_function(mf)
        else:
            node.set_editor_property("material_function", mf)
        for pin, src in inputs.items():
            self.link(src, node, pin)
        return Call(self, node)

    def comment(self, text):
        """A note on the node (shows as the node's bubble in the graph editor)."""
        return text


def connect_property(src: Out, prop):
    ok = MEL.connect_material_property(src.node, src.out, prop)
    if not ok:
        raise RuntimeError(f"connect_material_property failed: {src} -> {prop}")
