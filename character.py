from concurrent.futures import ProcessPoolExecutor
from typing import Set, Dict, Tuple, Union, List
from dataclasses import dataclass, field, asdict

ATTR = {"str": "strength", 
        "dex": "dexterity", 
        "int": "intelligence", 
        "wis": "wisdom", 
        "cha": "charisma", 
        "con": "constitution"}

ATTR_FLAT = tuple(list(ATTR.keys()) + list(ATTR.values()))

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
         "insight": "wisdom",
         "medicine": "wisdom",
         "perception": "wisdom",
         "survival": "wisdom",
         "deception": "charisma",
         "intimidation": "charisma",
         "performance": "charisma",
         "persuasion": "charisma"
        }    

FULL_SKILLLIST = tuple(list(SKILL.keys()) + list(ATTR_FLAT))

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

    def __str__(self):
        classstr = ", ".join(f"Level {cls.level} {cls.name.title()}" for cls in self.classes.values())
        namestr = f'**{self.name.title()}**: {self.race.title()} *({classstr})*'
        attrs = "\n".join(f"{attr.title()}: {getattr(self, attr)}" for attr in ATTR.values())
        profs = f"**Proficiencies**: {', '.join(map(str.title, self.proficiencies))}"
        return f"{namestr}\n{attrs}\n{profs}"
        
    @property
    def level(self):
        total_level = sum(cls.level for classname, cls in self.classes.items())
        return total_level or 1
    
    @property
    def proficiency(self):
        return (self.level + 3) // 4 + 1
    
    def add_proficiency(self, skill_or_attr: str):
        skill_or_attr = skill_or_attr.lower()
        if skill_or_attr not in SKILL and skill_or_attr not in ATTR_FLAT:
            raise ValueError('invalid skill name')
        self.proficiencies.add(ATTR.get(skill_or_attr, skill_or_attr))
        
    def update_class(self, classname: str, classlevel: int):
        classname = classname.lower()
        cls = self.classes.get(classname, Class(classname, classlevel))
        cls.level = classlevel
        self.classes[classname] = cls

    def get_class_level(self, cls: str) -> int:
        cls = self.classes.get(cls, None)
        return cls.level if cls is not None else 0

    def get_skill_modifiers(self, skill_or_attribute: str, saving_throw=False):
        skill_or_attribute = ATTR.get(skill_or_attribute, skill_or_attribute)
        if (skill := getattr(self, skill_or_attribute, None)) is not None:
            base_mod = (skill - 10) // 2
        else:
            attr = SKILL.get(skill_or_attribute)
            base_mod = (getattr(self, attr) - 10) // 2
        
        prof_mod = 0
        if skill_or_attribute in self.proficiencies:
            if saving_throw or skill_or_attribute in SKILL: 
                prof_mod = self.proficiency
        elif self.get_class_level('bard') >= 2:
            prof_mod = self.proficiency // 2

        other_mod = self.skill_modifiers.get(skill_or_attribute, ('', lambda char: 0))

        return (base_mod, prof_mod, other_mod)

    def get_modifier(self, skill_or_attribute: str, saving_throw=False):
        base_mod, prof_mod, other_mod_tup = self.get_skill_modifiers(skill_or_attribute, saving_throw)
        other_mod = other_mod_tup[1](self)
        return base_mod + prof_mod + other_mod

    def explain_modifier(self, skill_or_attribute: str, saving_throw=False):
        base_mod, prof_mod, other_mod = self.get_skill_modifiers(skill_or_attribute, saving_throw)
        total = self.get_modifier(skill_or_attribute, saving_throw)
        return f'{self.name.title()} {skill_or_attribute.title()}: **{total}**  *(Base Mod={base_mod}, Prof Mod: {prof_mod}, {other_mod[0].title() or "Other"}: {other_mod[1](self)})*'

    def create_skill_modifier(self, skill_or_attribute: str, name: str = None, modifier: int = 0, add_prof: bool = False):
        if skill_or_attribute not in FULL_SKILLLIST:
            raise AttributeError('invalid skill name')
        skillmod = SkillModifier(modifier, add_prof)
        self.skill_modifiers[skill_or_attribute] = (name or '', skillmod)

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


@dataclass
class SkillModifier(object):
    modifier: int
    add_proficiency: bool

    def __call__(self, char: Character):
        prof = char.proficiency
        return self.modifier + (prof if self.add_proficiency else 0)
