from concurrent.futures import ProcessPoolExecutor
from typing import Set, Dict, Tuple, Union, List
from dataclasses import dataclass, field, asdict

ATTR = {"strength", "dexterity", "intelligence", "wisdom", "charisma", "constitution"}

SKILL = {"athletics": "strength",
         "acrobatics": "dexterity",
         "sleight_of_hand": "dexterity",
         "stealth": "dexterity",
         "arcana": "intelligence",
         "history": "intelligence",
         "investigation": "intelligence",
         "nature": "intelligence",
         "religion": "intelligence",
         "animal_handling": "wisdom",
         "insignt": "wisdom",
         "medicine": "wisdom",
         "perception": "wisdom",
         "survival": "wisdom",
         "deception": "charisma",
         "intimidation": "charisma",
         "performance": "charisma",
         "persuasion": "charisma"
        }    

@dataclass
class Class():
    name: str
    level: int
        
    # disallows duplicate classes in a set
    def __hash__(self):
        return hash(self.name)

@dataclass
class Character():
    name: str
    race: str
    strength: int
    dexterity: int
    constitution: int
    intelligence: int
    wisdom: int
    charisma: int
    proficiencies: Set[str] = field(default_factory=set)
    skill_modifiers: Dict[str, Tuple[str, int]] = field(default_factory=dict)
    classes: Dict[str, Class] = field(default_factory=dict)
        
    def __eq__(self, other):
        if isinstance(other, Character):
            return (self.name == other.name)
        return False
        
    @property
    def level(self):
        total_level = sum(cls.level for classname, cls in self.classes.items())
        return total_level or 1
    
    @property
    def proficiency(self):
        return (self.level + 3) // 4 + 1
    
    def add_proficiency(self, skill_or_attr: str):
        skill_or_attr = skill_or_attr.lower()
        if skill not in SKILL and skill not in ATTR:
            raise ValueError('invalid skill name')
        self.proficiencies.add(skill)
        
    def add_class(self, cls: Class):
        if not isinstance(cls, Class):
            raise Exception('can only add Class objects')
        self.classes.add(cls)

    def get_class_level(self, cls: str) -> int:
        cls = self.classes.get(cls, None)
        return cls.level if cls is not None else 0

    def get_modifier(self, skill_or_attribute: str, saving_throw=False):
        skill_or_attribute = skill_or_attribute.lower()
        if (skill := getattr(self, skill_or_attribute, None)) is not None:
            return (skill - 10) // 2
        
        attr = SKILL.get(skill_or_attribute)
        base_mod = (getattr(self, attr) - 10) // 2
        
        prof_mod = 0
        if skill_or_attribute in self.proficiencies:
            if saving_throw or skill_or_attribute in SKILL: 
                prof_mod = self.proficiency
        elif self.get_class_level('bard') >= 2:
            prof_mod = self.proficiency // 2
        
        return base_mod + prof_mod

Owner = str
CharacterName = str

@dataclass
class Rolodex():
    owners: Dict[CharacterName, Set[Owner]] = field(default_factory=dict)
    characters: Dict[CharacterName, Character] = field(default_factory=dict)

    def __len__(self):
        return len(self.characters)
        
    def add_character(self, owners: Union[Owner, List[Owner]], character: Character):
        if character.name in self.characters:
            raise Exception("character is already in rolodex!")
        if len(owners) == 0:
            raise Exception("someone must own the character")
        if isinstance(owners, str):
            owners = [owners]
        self.characters[character.name.lower()] = character
        self.owners[character.name.lower()] = owners
        
    def get_character(self, user: str, character_name: str):
        character_name = character_name.lower()
        if character_name not in self.characters:
            raise ValueError("there is no character by this name")
        if user not in self.owners[character_name]:
            raise PermissionError("you cannot access this character")
        return self.characters[character_name]
    
    def store(self):
        with open('characters.txt', 'w') as fout: 
            fout.write(str(self.__dict__))
            
    @staticmethod
    def load():
        with open('characters.txt', 'r') as fin:
            rawdata = fin.read()
        if rawdata:
            data = eval(rawdata)
            return Rolodex(**data)
        else:
            return Rolodex()

