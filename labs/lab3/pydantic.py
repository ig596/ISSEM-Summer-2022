"""
Basic example showing how to read and validate data from a file using Pydantic.
"""

"""
Sample data file:
[
  {
    "title": "Zero to One",
    "subtitle": "Notes on Startups, or How to Build the Future",
    "author": "Peter Thiel",
    "publisher": "Ballantine Books",
    "isbn_10": "0753555190",
    "isbn_13": "978-0753555194",
    "price": 14.29,
    "author2": {
      "name": "Peter Thiel",
      "verified": true
    }
  }
]
"""

import json
from typing import List, Optional

import pydantic


class ISBNMissingError(Exception):

    def __init__(self, title: str, message: str) -> None:
        self.title = title
        self.message = message
        super().__init__(message)


class ISBN10FormatError(Exception):

    def __init__(self, value: str, message: str) -> None:
        self.value = value
        self.message = message
        super().__init__(message)


class Author(pydantic.BaseModel):
    name: str
    verified: bool


class Book(pydantic.BaseModel):

    title: str
    author: str
    publisher: str
    price: float
    isbn_10: Optional[str]
    isbn_13: Optional[str]
    subtitle: Optional[str]
    author2: Optional[Author]

    @pydantic.root_validator(pre=True)
    @classmethod
    def check_isbn_10_or_13(cls, values):
        if "isbn_10" not in values and "isbn_13" not in values:
            raise ISBNMissingError(
                title=values["title"],
                message="Document should have either an ISBN10 or ISBN13",
            )
        return values

    @pydantic.validator("isbn_10")
    @classmethod
    def isbn_10_valid(cls, value) -> None:
        chars = [c for c in value if c in "0123456789Xx"]
        if len(chars) != 10:
            raise ISBN10FormatError(value=value, message="ISBN10 should be 10 digits.")

        def char_to_int(char: str) -> int:
            if char in "Xx":
                return 10
            return int(char)

        if sum((10 - i) * char_to_int(x) for i, x in enumerate(chars)) % 11 != 0:
            raise ISBN10FormatError(
                value=value, message="ISBN10 digit sum should be divisible by 11."
            )
        return value

    class Config:

        allow_mutation = False
        anystr_lower = True


def main() -> None:

    # Read data from a JSON file
    with open("./data.json") as file:
        data = json.load(file)
        books: List[Book] = [Book(**item) for item in data]
        print(books)
        print(books[0])
        print(books[0].dict(exclude={"price"}))
        print(books[1].copy())


if __name__ == "__main__":
    main()