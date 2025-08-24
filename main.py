# TODO:
# - Keep track of:
#   - Which value in each register allocation table is the biggest
#   - Which value in each row is the biggest (excluding the biggest value in the table)
# - Stop the variable links from overlapping each other
# - Show a detailed example of allocating registers with all of the known cases where getting the ideal allocations is hard

from dataclasses import dataclass, field

import manim
from manim.typing import Point3D
from typing import Mapping, TypeAlias, TypeVar, Any, Type, Self, Tuple
import copy
import math
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
    arrow: manim.LabeledLine

registerPrioraties: TypeAlias = list[int]

@(dataclass)
class registerPrioratiesAndLinks:
    links: list[variableLink]
    prioraties: registerPrioraties = field(default_factory=lambda: [0,0,0,0,0])

@(dataclass)
class registerAllocationTable():
    data: Mapping[str, registerPrioratiesAndLinks]
    backingTable: manim.Table

t = TypeVar("t")
sequence: TypeAlias = list[t] | tuple[t, ...]

manimText: TypeAlias = manim.Text | manim.MathTex | manim.Tex

# `manim.Text`, `manim.MathTex` and `manim.Tex` have slightly different text
# rendering, so this function is used everywhere that there is a piece of text
# so that every piece of text has the same text rendering.
def text(t: str, font_size: float = manim.DEFAULT_FONT_SIZE) -> manimText:
    return manim.Text(t, font_size=font_size)

def intsToListOfVMobjects(tuple: sequence[int]) -> list[manim.VMobject]:
    return [text(str(val)) for val in tuple]

def generateRegisterAllocationTable(*variables: str) -> registerAllocationTable:
    data: Mapping[str, registerPrioratiesAndLinks] = {}
    for var in variables:
        data[var] = registerPrioratiesAndLinks([])
    return registerAllocationTable(
        data,
        manim.MobjectTable(
            [intsToListOfVMobjects(val.prioraties) for val in data.values()],
            col_labels=[text(f"r{i}") for i in range(number_of_registers)] + [text("Unknown")],
            row_labels=[text(key) for key in data.keys()],
        ),
    )

@(dataclass)
class registerAllocationGraph:
    tables: list[registerAllocationTable]
    scene: manim.Scene

t = TypeVar("t")
def iterateToSolution(goal: float, min: int, max: int, func: Callable[[int], Tuple[float, t]]) -> Tuple[float, t]:
    input = math.ceil((min+max)/2)
    while True:
        value, output = func(input)
        if value > goal:
            max = input
        else:
            min = input
        newInput = math.ceil((min+max)/2)
        if input == newInput:
            return input, output
        input = newInput

def arrangeInGrid(targetWidth: float, targetHeight: float, padding: float, *elems: manim.Mobject):
    # Find the ideal number columns to be as close to the target aspect ratio as possible
    targetAspectRatio = targetWidth/targetHeight
    def calculateAspectRatio(numberOfColumns: int) -> Tuple[float, Tuple[float, float, list[float], list[float]]]:
        numberOfRows = math.ceil(len(elems)/numberOfColumns)
        columnWidths = [0.0] * numberOfColumns
        rowHeights = [0.0] * numberOfRows
        for i, elem in enumerate(elems):
            x = i % numberOfColumns
            y = math.floor(i / numberOfColumns)
            if elem.height > rowHeights[y]:
                rowHeights[y] = elem.height
            if elem.width > columnWidths[x]:
                columnWidths[x] = elem.width
        width = padding*(numberOfColumns-1)
        height = padding*(numberOfRows-1)
        for i in range(0, numberOfColumns):
            width += columnWidths[i]
        for i in range(0, numberOfRows):
            height += rowHeights[i]
        return width / height, (width, height, columnWidths, rowHeights)
    aspectRatio, (width, height, columnWidths, rowHeights) = iterateToSolution(targetAspectRatio, 0, len(elems), calculateAspectRatio)

    # Expand or shrink the grid so it fits within `width` and `height`
    if targetAspectRatio > aspectRatio:
        scale = targetHeight / height
    else:
        scale = targetWidth / width

    # Get the centers of every element in the table based on the column and row sizes
    y = height/2
    elementCenters: list[Tuple[float, float, float]] = []
    for rowHeight in rowHeights:
        x = -width/2
        for columnWidth in columnWidths:
            elementCenters += [((x+columnWidth/2)*scale, (y - rowHeight/2)*scale, 0)]
            x += columnWidth + padding
        y -= rowHeight + padding

    # Position every element in the table according to their center
    for center, elem in zip(elementCenters, elems):
        elem.scale(scale)
        elem.move_to(center)

def generateRegisterAllocationGraph(scene: manim.Scene, *varNamesList: list[str]) -> registerAllocationGraph:
    out = registerAllocationGraph(
        [generateRegisterAllocationTable(*varNames) for varNames in varNamesList],
        scene,
    )
    padding = 0.5
    width = convertToType(out.scene.camera.frame_width, float)
    height = convertToType(out.scene.camera.frame_height, float)
    arrangeInGrid(width-padding, height-padding, padding, *[t.backingTable for t in out.tables])
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

@(dataclass)
class number:
    backingMobject: manimText
    value: int
    def copy(self) -> Self:
        return copy.deepcopy(self)

def getCellFromVarRefAndRegister(graph: registerAllocationGraph, varRef: variableReference, register: int) -> number:
    row, rowData = getRowFromVarRef(graph, varRef)
    return number(convertToType(row[register+1], manim.Text), rowData.prioraties[register])

t = TypeVar('t')
def convertToType(instance: Any, target_type: Type[t]) -> t:
    if not isinstance(instance, target_type):
        raise AssertionError("Expected ", target_type, "got type", instance)
    return instance

def addToTableCell(
    graph: registerAllocationGraph,
    varRef: variableReference,
    register: int,
    added: number,
):
    cell = getCellFromVarRefAndRegister(graph, varRef, register)

    # Animation 1
    cellTarget = cell.backingMobject.copy()
    operation = text("+" if added.value >= 0 else "-", font_size=cell.backingMobject.font_size)
    valueTarget = added.backingMobject.copy()
    valueTarget.height = cell.backingMobject.height
    rowItems = [cellTarget, operation, valueTarget]
    arrangeInRow(cell.backingMobject.get_center(), 0.02, *rowItems)
    graph.scene.play(manim.AnimationGroup(
        manim.ReplacementTransform(cell.backingMobject, cellTarget),
        manim.ReplacementTransform(added.backingMobject, valueTarget),
        manim.Create(operation),
    ))

    # Animation 2
    group = manim.Group(*rowItems)
    resultMobject = text(str(cell.value+added.value), font_size=cell.backingMobject.font_size)
    resultMobject.move_to(group.get_center())
    graph.scene.play(manim.ReplacementTransform(group, resultMobject))

    # Update the prioraty in the table cell
    graph.tables[varRef.indexOfRegisterAllocationTable].data[varRef.nameOfVariableWithinTable].prioraties[register] += added.value

    # Update the mobject in the table cell
    referencedVariableIndex = list(graph.tables[varRef.indexOfRegisterAllocationTable].data.keys()).index(varRef.nameOfVariableWithinTable)
    graph.tables[varRef.indexOfRegisterAllocationTable].backingTable.mob_table[referencedVariableIndex+1][register+1] = resultMobject

def createLink(fromVar: variableReference, toVar: variableReference, strength: int) -> Callable[[registerAllocationGraph], registerAllocationGraph]:
    def createLinkFunc(graph: registerAllocationGraph) -> registerAllocationGraph:
        fromRowMobjects, _fromRowData = getRowFromVarRef(graph, fromVar)
        toRowMobjects, _toRowData = getRowFromVarRef(graph, toVar)
        arrow = manim.LabeledLine(text(str(strength)), start=fromRowMobjects, end=toRowMobjects)
        fromLink = variableLink(toVar, strength, arrow)
        toLink = variableLink(fromVar, strength, arrow)
        graph.tables[fromVar.indexOfRegisterAllocationTable].data[fromVar.nameOfVariableWithinTable].links.append(fromLink)
        graph.tables[toVar.indexOfRegisterAllocationTable].data[toVar.nameOfVariableWithinTable].links.append(toLink)
        graph.scene.play(manim.Create(arrow))
        added = number(arrow.label.rendered_label, strength)
        addToTableCell(graph, fromVar, number_of_registers, added.copy())
        addToTableCell(graph, toVar, number_of_registers, added.copy())
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

def arrangeInRow(center: Point3D, padding: float, *elements: manim.Mobject):
    totalWidth = -padding
    for elem in elements:
        totalWidth += elem.width + padding
    currentPos = center
    currentPos[0] -= totalWidth/2
    for elem in elements:
        elem.move_to(currentPos, manim.LEFT)
        currentPos[0] += elem.width + padding

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
        graph.scene.play(manim.AnimationGroup(
            manim.ReplacementTransform(reg, regTarget),
            crossoutMobjectsAnimation(*row.submobjects[1:]),
            crossoutMobjectsAnimation(*col.submobjects[0:]),
        ))
        for link in rowData.links:
            label = link.arrow.label.rendered_label
            addToTableCell(graph, link.variable, register, number(label.copy(), link.strength))
            addToTableCell(graph, link.variable, number_of_registers, number(label.copy(), -link.strength))
            graph.scene.play(manim.Uncreate(link.arrow))
            graph.tables[link.variable.indexOfRegisterAllocationTable].data[link.variable.nameOfVariableWithinTable].links = filter(
                graph.tables[link.variable.indexOfRegisterAllocationTable].data[link.variable.nameOfVariableWithinTable].links,
                lambda link: link.variable == var,
            )
        graph.tables[var.indexOfRegisterAllocationTable].data[var.nameOfVariableWithinTable].links = []
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
