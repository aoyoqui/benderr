import pytest
from dataclasses import dataclass
from pydantic.dataclasses import dataclass as pddataclass

from br_tester.sequence import Sequence
from br_tester.sequence_check import extract_steps_with_return


@dataclass
class CustomDataClass:
    pass

class CustomClass:
    pass

@pddataclass
class CustomPydanticDataClass:
    pass

class TestSequence(Sequence):
    __test__ = False
    def sequence(self):
        self.step(lambda : True)
        self.step(self.return_unknown)
        self.step(self.return_boolean)
        self.step(self.return_string)
        self.step(self.return_number)
        self.step(self.return_none_but_type_number)
        self.step(self.return_dataclass)
        self.step(self.return_class)
        self.step(self.return_pydantic_dataclass)
        result = self.step(self.return_integer)
        self.step(self.return_none_with_arguments, result)
        self.step(self.return_tuple)
        self.step(self.return_annotated_tuple)

    def return_unknown(self):
        return True

    def return_boolean(self) -> bool:
        return False    

    def return_string(self) -> str:
        return "foo"
    
    def return_number(self) -> float:
        return 1.0
    
    def return_none_but_type_number(self) -> int:
        pass

    def return_dataclass(self) -> CustomDataClass:
        return CustomDataClass()

    def return_class(self) -> CustomClass:
        return CustomClass()
    
    def return_pydantic_dataclass(self) -> CustomPydanticDataClass:
        return CustomPydanticDataClass()
    
    def return_integer(self) -> int:
        return 2
    
    def return_none_with_argument(self, _):
        pass

    def return_tuple(self) -> tuple:
        return "success", True

    def return_annotated_tuple(self) -> tuple[int, int]:
        return 1, True

def test_sequence_check():
    steps = extract_steps_with_return(TestSequence)
    print(steps)
    assert len(steps) == 13
    assert steps[0][0] == "lambda"
    assert steps[0][1] == "bool"
    assert steps[1][0] == "return_unknown"
    assert steps[1][1] == "none"
    assert steps[2][0] == "return_boolean"
    assert steps[2][1] == "bool"
    assert steps[3][0] == "return_string"
    assert steps[3][1] == "str"
    assert steps[4][0] == "return_number"
    assert steps[4][1] == "numeric"
    assert steps[5][0] == "return_none_but_type_number"
    assert steps[5][1] == "numeric"
    assert steps[6][0] == "return_dataclass"
    assert steps[6][1] == "CustomDataClass"
    assert steps[7][0] == "return_class"
    assert steps[7][1] == "CustomClass"
    assert steps[8][0] == "return_pydantic_dataclass"
    assert steps[8][1] == "CustomPydanticDataClass"
    assert steps[9][0] == "return_integer"
    assert steps[9][1] == "numeric"
    assert steps[10][0] == "return_none_with_arguments"
    assert steps[10][1] == "none"
    assert steps[11][0] == "return_tuple"
    assert steps[11][1] == "tuple"
    assert steps[12][0] == "return_annotated_tuple"
    assert steps[12][1] == "tuple[int, int]"

if __name__ == "__main__":
    pytest.main(["-v"])
