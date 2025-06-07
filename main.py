# TODO:
# - Keep track of:
#   - Which value in each register allocation table is the biggest
#   - Which value in each row is the biggest (excluding the biggest value in the table)
# - Partially done: Update the register prioraties for other tables when a register is allocated in one table
# - Show a detailed example of allocating registers with all of the known cases where getting the ideal allocations is hard

from dataclasses import dataclass

import manim
from manim.typing import Point3D
from typing import Tuple, Mapping, TypeAlias, TypeVar, Any, Type
from collections.abc import Callable

number_of_registers = 4

@(dataclass)
class variableReference:
    indexOfRegisterAllocationTable: int
    nameOfVariableWithinTable: str

@(dataclass)
class variableLink:
    variable: variableReference
    strength: int
    arrow: manim.LabeledArrow

registerPrioraties: TypeAlias = Tuple[int, int, int, int, int]

@(dataclass)
class registerPrioratiesAndLinks:
    links: list[variableLink]
    prioraties: registerPrioraties = (0, 0, 0, 0, 0)

@(dataclass)
class registerAllocationTable():
    data: Mapping[str, registerPrioratiesAndLinks]
    backingTable: manim.Table

def tupleOfIntsToListOfVMobjects(tuple: Tuple[int, ...]) -> list[manim.VMobject]:
    return [manim.Text(str(val)) for val in tuple]

def generateRegisterAllocationTable(*variables: str) -> registerAllocationTable:
    data: Mapping[str, registerPrioratiesAndLinks] = {}
    for var in variables:
        data[var] = registerPrioratiesAndLinks([])
    return registerAllocationTable(
        data,
        manim.MobjectTable(
            [tupleOfIntsToListOfVMobjects(val.prioraties) for val in data.values()],
            col_labels=[manim.Text(f"r{i}") for i in range(number_of_registers)] + [manim.Text("Unkown")],
            row_labels=[manim.Text(key) for key in data.keys()],
        ),
    )

@(dataclass)
class registerAllocationGraph:
    tables: list[registerAllocationTable]
    scene: manim.Scene

def generateRegisterAllocationGraph(scene: manim.Scene, *varNamesList: list[str]) -> registerAllocationGraph:
    out = registerAllocationGraph(
        [generateRegisterAllocationTable(*varNames) for varNames in varNamesList],
        scene,
    )
    tablesGroup = manim.Group(*[t.backingTable for t in out.tables])
    tablesGroup.scale(0.3)
    tablesGroup.arrange_in_grid(buff=1)
    out.scene.play(manim.LaggedStart(
        *[manim.FadeIn(table.backingTable) for table in out.tables],
        lag_ratio=0.5,
    ))
    return out

def getRowFromVarRef(graph: registerAllocationGraph, varRef: variableReference) -> tuple[manim.VMobject, registerPrioratiesAndLinks]:
    table = graph.tables[varRef.indexOfRegisterAllocationTable]
    referencedVariableIndex = list(table.data.keys()).index(varRef.nameOfVariableWithinTable)
    return table.backingTable.get_rows().submobjects[referencedVariableIndex+1], table.data[varRef.nameOfVariableWithinTable]

def getColFromRegister(table: registerAllocationTable, register: int) -> manim.VMobject:
    return table.backingTable.get_columns().submobjects[register+1]

def getCellFromVarRefAndRegister(graph: registerAllocationGraph, varRef: variableReference, register: int) -> manim.Text:
    row, _ = getRowFromVarRef(graph, varRef)
    return convertToType(row[register+1], manim.Text)

T = TypeVar('T')
def convertToType(instance: Any, target_type: Type[T]) -> T:
    assert isinstance(instance, target_type)
    return instance

def createLink(fromVar: variableReference, toVar: variableReference, strength: int) -> Callable[[registerAllocationGraph], registerAllocationGraph]:
    def createLinkFunc(graph: registerAllocationGraph) -> registerAllocationGraph:
        fromRowMobjects, _fromRowData = getRowFromVarRef(graph, fromVar)
        toRowMobjects, _toRowData = getRowFromVarRef(graph, toVar)
        arrow = manim.LabeledArrow(str(strength), start=fromRowMobjects, end=toRowMobjects)
        fromLink = variableLink(toVar, strength, arrow)
        toLink = variableLink(fromVar, strength, arrow)
        graph.tables[fromVar.indexOfRegisterAllocationTable].data[fromVar.nameOfVariableWithinTable].links.append(fromLink)
        graph.tables[toVar.indexOfRegisterAllocationTable].data[toVar.nameOfVariableWithinTable].links.append(toLink)
        graph.scene.play(manim.Create(arrow))
        return graph
    return createLinkFunc

def crossoutMobjectsAnimation(*mobjects: manim.Mobject) -> manim.LaggedStart:
    return manim.LaggedStart(
        *[manim.Create(manim.Cross(mobject, stroke_width=2)) for mobject in mobjects],
        lag_ratio=0.5,
        run_time=1.5,
    )

def x(point: Point3D) -> float:
    return point[0]

def y(point: Point3D) -> float:
    return point[1]

def set_left(object: manim.Mobject, x_coord: float):
    object.set_x(x_coord + object.width/2)

def set_right(object: manim.Mobject, x_coord: float):
    object.set_x(x_coord - object.width/2)

def set_bottom(object: manim.Mobject, y_coord: float):
    object.set_y(y_coord - object.height/2)

a = TypeVar("a")
def filter(l: list[a], func: Callable[[a], bool]) -> list[a]:
    indexesToDelete: list[int] = []
    for index, item in enumerate(l):
        if func(item):
            indexesToDelete += [index]
    removed = 0
    for index in indexesToDelete:
        del l[index-removed]
        removed += 1
    return l

def arrangeInRow(centerX: float, centerY: float, padding: float, *elements: manim.Mobject):
    totalWidth = -padding
    for elem in elements:
        totalWidth += elem.width + padding
    currentPos = centerX - totalWidth/2
    for elem in elements:
        set_left(elem, currentPos)
        elem.set_y(centerY)
        currentPos += elem.width + padding

def allocateRegisterToVariable(var: variableReference, register: int) -> Callable[[registerAllocationGraph], registerAllocationGraph]:
    def allocateRegisterToVariableFunc(graph: registerAllocationGraph) -> registerAllocationGraph:
        table = graph.tables[var.indexOfRegisterAllocationTable]
        row, rowData = getRowFromVarRef(graph, var)

        reg = convertToType(getColFromRegister(table, register)[0], manim.Text).copy()
        regTarget = reg.copy()
        regTarget.scale(0.5)
        align_to = row.submobjects[0]
        set_left(regTarget, x(align_to.get_right()))
        regTarget.set_y(y(align_to.get_bottom()))
        col = getColFromRegister(table, register)
        moveArrowStrengthsToRegisterPrioratiesAnimations: list[manim.Animation] = []
        for link in rowData.links:
            tableCell = getCellFromVarRefAndRegister(graph, link.variable, register)
            tableCellTarget = tableCell.copy()
            plusSign = manim.Text("+", font_size=tableCell.font_size)
            newStrengthLabel = manim.Text(str(link.strength), font_size=tableCell.font_size)
            graph.scene.remove(link.arrow.label.rendered_label)
            arrangeInRow(tableCell.get_x(), tableCell.get_y(), 0.02, tableCellTarget, plusSign, newStrengthLabel)
            moveArrowStrengthsToRegisterPrioratiesAnimations += [
                manim.Transform(link.arrow.label.rendered_label.copy(), newStrengthLabel),
                manim.Transform(tableCell, tableCellTarget),
                manim.Create(plusSign),
                manim.Uncreate(link.arrow),
            ]
            graph.tables[link.variable.indexOfRegisterAllocationTable].data[link.variable.nameOfVariableWithinTable].links = filter(
                graph.tables[link.variable.indexOfRegisterAllocationTable].data[link.variable.nameOfVariableWithinTable].links,
                lambda link: link.variable == var,
            )
        rowData.links = []
        graph.scene.play(manim.AnimationGroup(
            *moveArrowStrengthsToRegisterPrioratiesAnimations,
            manim.Transform(reg, regTarget),
            crossoutMobjectsAnimation(*row.submobjects[1:]),
            crossoutMobjectsAnimation(*col.submobjects[0:]),
        ))
        return graph
    return allocateRegisterToVariableFunc

a = TypeVar("a")
def pipe(data: a, *funcs: Callable[[a], a]) -> a:
    for func in funcs:
        data = func(data)
    return data

class DefaultTemplate(manim.Scene):
    def construct(self):
        self = pipe(
            generateRegisterAllocationGraph(
                self,
                ["index"],
                ["index", "number"],
            ),
            createLink(variableReference(0, "index"), variableReference(1, "number"), 1),
            createLink(variableReference(0, "index"), variableReference(1, "index"), 1),
            allocateRegisterToVariable(variableReference(1, "index"), 1),
        ).scene
