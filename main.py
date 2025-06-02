# TODO:
# - Keep track of:
#   - Which value in each register allocation table is the biggest
#   - Which value in each row is the biggest (excluding the biggest value in the table)
# - Update the register prioraties for other tables when a register is allocated in one table
# - Show a detailed example of allocating registers with all of the known cases where getting the ideal allocations is hard

from dataclasses import dataclass

import manim
from typing import Tuple, Mapping, TypeAlias, TypeVar
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
    arrow: manim.Arrow

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
    animations: list[manim.Animation]

def generateRegisterAllocationGraph(*varNamesList: list[str]) -> registerAllocationGraph:
    out = registerAllocationGraph(
        [generateRegisterAllocationTable(*varNames) for varNames in varNamesList],
        [],
    )
    out.animations += [manim.LaggedStart(
        *[manim.FadeIn(table.backingTable) for table in out.tables],
        lag_ratio=0.5,
    )]
    tablesGroup = manim.Group(*[t.backingTable for t in out.tables])
    tablesGroup.scale(0.3)
    tablesGroup.arrange_in_grid(buff=1)
    return out

def getRowFromVarName(table: registerAllocationTable, varName: str) -> tuple[manim.VMobject, registerPrioratiesAndLinks]:
    referencedVariableIndex = list(table.data.keys()).index(varName)
    return table.backingTable.get_rows().submobjects[referencedVariableIndex+1], table.data[varName]

def getColFromRegister(graph: registerAllocationGraph, indexOfRegisterAllocationTable: int, register: int) -> manim.VMobject:
    referencedTable = graph.tables[indexOfRegisterAllocationTable]
    return referencedTable.backingTable.get_columns().submobjects[register+1]

def createLink(fromVar: variableReference, toVar: variableReference, strength: int) -> Callable[[registerAllocationGraph], registerAllocationGraph]:
    def createLinkFunc(graph: registerAllocationGraph) -> registerAllocationGraph:
        fromTable = graph.tables[fromVar.indexOfRegisterAllocationTable]
        toTable = graph.tables[toVar.indexOfRegisterAllocationTable]
        fromRowMobjects, fromRowData = getRowFromVarName(fromTable, fromVar.nameOfVariableWithinTable)
        toRowMobjects, toRowData = getRowFromVarName(toTable, toVar.nameOfVariableWithinTable)
        arrow = manim.LabeledArrow(str(strength), start=fromRowMobjects, end=toRowMobjects)
        fromLink = variableLink(toVar, strength, arrow)
        toLink = variableLink(fromVar, strength, arrow)
        graph.tables[fromVar.indexOfRegisterAllocationTable].data[fromVar.nameOfVariableWithinTable].links.append(fromLink)
        graph.tables[toVar.indexOfRegisterAllocationTable].data[toVar.nameOfVariableWithinTable].links.append(toLink)
        graph.animations += [manim.Create(arrow)]
        return graph
    return createLinkFunc

def crossoutMobjectsAnimation(*mobjects: manim.Mobject) -> manim.LaggedStart:
    return manim.LaggedStart(
        *[manim.Create(manim.Cross(mobject, stroke_width=2)) for mobject in mobjects],
        lag_ratio=0.5,
        run_time=1.5,
    )

def set_left(object: manim.Mobject, x_coord: float):
    center_to_right_delta = object.get_right()[0] - object.get_center()[0]
    object.set_x(x_coord + center_to_right_delta)

def set_right(object: manim.Mobject, x_coord: float):
    center_to_right_delta = object.get_right()[0] - object.get_center()[0]
    object.set_x(x_coord - center_to_right_delta)

def set_bottom(object: manim.Mobject, y_coord: float):
    center_to_bottom_delta = object.get_bottom()[1] - object.get_center()[1]
    object.set_y(y_coord - center_to_bottom_delta)

def allocateRegisterToVariable(var: variableReference, register: int) -> Callable[[registerAllocationGraph], registerAllocationGraph]:
    def allocateRegisterToVariableFunc(graph: registerAllocationGraph) -> registerAllocationGraph:
        table = graph.tables[var.indexOfRegisterAllocationTable]
        row, rowData = getRowFromVarName(table, var.nameOfVariableWithinTable)

        # variableText = row.submobjects[0]
        # variableRectangle = table.get_cell((1, variableIndex+2))

        reg = table.backingTable.elements.submobjects[register]
        reg2 = reg.copy()
        reg2.generate_target()
        reg2.target.scale(0.5)
        align_to = row.submobjects[0]
        set_left(reg2.target, align_to.get_right()[0])
        reg2.target.set_y(align_to.get_bottom()[1])
        col = getColFromRegister(graph, var.indexOfRegisterAllocationTable, register)
        arrowsToUncreate = [link.arrow for link in rowData.links]

        graph.animations += [manim.AnimationGroup(
            # *[manim.Uncreate(arrow) for arrow in arrowsToUncreate],
            *[manim.Indicate(arrow.label) for arrow in arrowsToUncreate],
            manim.MoveToTarget(reg2),
            crossoutMobjectsAnimation(*row.submobjects[1:]),
            crossoutMobjectsAnimation(*col.submobjects[0:]),
        )]
        return graph
    return allocateRegisterToVariableFunc

a = TypeVar("a")
def pipe(data: a, *funcs: Callable[[a], a]) -> a:
    for func in funcs:
        data = func(data)
    return data

class DefaultTemplate(manim.Scene):
    def construct(self):
        graph = pipe(
            generateRegisterAllocationGraph(
                ["index"],
                ["index", "number"],
            ),
            createLink(variableReference(0, "index"), variableReference(1, "number"), 1),
            createLink(variableReference(0, "index"), variableReference(1, "index"), 1),
            allocateRegisterToVariable(variableReference(1, "index"), 1),
        )
        for anim in graph.animations:
            self.play(anim)
        # self.wait()
