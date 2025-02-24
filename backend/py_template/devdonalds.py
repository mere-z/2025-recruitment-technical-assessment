from dataclasses import dataclass
from typing import List, Dict, Union
from flask import Flask, request, jsonify
import re

# ==== Type Definitions, feel free to add or modify ===========================
@dataclass
class CookbookEntry:
	name: str

@dataclass
class RequiredItem():
	name: str
	quantity: int

@dataclass
class Recipe(CookbookEntry):
	required_items: List[RequiredItem]

@dataclass
class Ingredient(CookbookEntry):
	cook_time: int


# =============================================================================
# ==== HTTP Endpoint Stubs ====================================================
# =============================================================================
app = Flask(__name__)

# Store your recipes here!
# We can use a dictionary because entry names are unique
cookbook = {}

# Task 1 helper (don't touch)
@app.route("/parse", methods=['POST'])
def parse():
	data = request.get_json()
	recipe_name = data.get('input', '')
	parsed_name = parse_handwriting(recipe_name)
	if parsed_name is None:
		return 'Invalid recipe name', 400
	return jsonify({'msg': parsed_name}), 200

# [TASK 1] ====================================================================
# Takes in a recipeName and returns it in a form that 
def parse_handwriting(recipeName: str) -> Union[str | None]:
	# Replaces any amount of whitespace, hyphens or underscores (+) with a single whitespace
	# Trims leading/trailing whitespace with .strip()
	recipeName = re.sub(r'[\s_-]+', ' ', recipeName).strip()

	# Deletes non whitespace/letters
	recipeName = re.sub(r'[^\sA-Za-z]', '', recipeName)
	
	if len(recipeName) == 0:
		return None
	else:
		# Capitalises every word and makes the rest of the word lowercase
		return recipeName.title()


# [TASK 2] ====================================================================
# Endpoint that adds a CookbookEntry to your magical cookbook
@app.route('/entry', methods=['POST'])
def create_entry():
	entry = request.get_json()

	if not entry:
		return "Invalid entry format", 400
		
	type = entry.get("type")
	name = entry.get("name")
	requiredItems = entry.get("requiredItems") if type == "recipe" else None
	cookTime = entry.get("cookTime") if type == "ingredient" else None

	if type not in ("recipe", "ingredient"):
		return "Type must be recipe or ingredient", 400


	# Name is a required field and must be a string
	if not name or not isinstance(name, str):
		return "Invalid name", 400

	# Cooktime must exist for ingredients, be an 'int' and be >= 0
	if type == "ingredient":
		if cookTime is None or not isinstance(cookTime, int) or cookTime < 0:
			return "Invalid cookTime", 400
	# Entry names must be unique, check existing cookbook
	if name in cookbook:
		return "Entry names must be unique", 400

	# Recipe required items must have only 1 element of the same name 
	if type == "recipe":
		if requiredItems is None or not isinstance(requiredItems, list):
			return "Invalid requiredItems", 400
		seen = set()

		for element in requiredItems:
			requiredName = element.get("name")
			if not requiredName or not isinstance(requiredName, str):
				return "Invalid requiredItem name", 400

			if requiredName in seen:
				return "Invalid required items, multiple of the same name", 400
			
			quantity = element.get("quantity")
			if quantity is None or not isinstance(quantity, int):
				return "Invalid requiredItem quantity", 400
		
			seen.add(requiredName)

	# Validation passed, add entry to cookbook
	cookbook[name] = entry
	
	return '', 200


# [TASK 3] ====================================================================
# Endpoint that returns a summary of a recipe that corresponds to a query name
@app.route('/summary', methods=['GET'])
def summary():
	# Endpoint takes in: /summary?name=<insert name here>
	recipe = request.args.get('name')

	if not recipe or recipe not in cookbook:
		return 'Recipe not found', 400
	
	entry = cookbook[recipe]

	# Check the type
	if entry.get("type") != 'recipe':
		return 'Can only summarise recipe types', 400

	# We can recursively buld up the ingredients list, and compute total cook time *later* as it'll just be quantity * ingredient
	try:
		base_ingredients = get_base_ingredient_counts(recipe, 1)
	except Exception as e:
		return 'A base ingredient provided does not exist in the cookbook', 400

	# Calculate the total cooktime from our base ingredients list
	totalCookTime = 0
	ingredientsList = []
	for ingredientName, quantity in base_ingredients.items():
		# Shouldn't need to error check ingredientNames at this step because we checked inside recursive function
		ingredient = cookbook[ingredientName]
		cookTime = ingredient.get('cookTime', 0)
		totalCookTime += quantity * cookTime
		ingredientsList.append({'name': ingredientName, 'quantity': quantity})

	
	summary = {
		'name': recipe,
		'cookTime': totalCookTime,
		'ingredients': ingredientsList  
	}

	return jsonify(summary), 200

def get_base_ingredient_counts(name, multiplier):

	if name not in cookbook:
		raise Exception(f"Cannot find {name} in cookbook")
	
	entry = cookbook[name]

	# Base case: Once we recurse down to an ingredient, return the quantity and name 
	if entry.get('type') == 'ingredient':
		return {name: multiplier}
	elif entry.get('type') == 'recipe':

		# Recursively build up a list of raw ingredients needed
		result = {}

		# Parses all requiredItems, going recursively to calculate how many ingredients needed/which if needed
		for item in entry.get('requiredItems'):
			subName = item.get('name')
			quantity = item.get('quantity')

			# The total count of ingredients that we need is the multiplier for the recipe (e.g. 3 meatballs) 
			# * by the quantity of ingredients needed to make 1 meatball
			subResult = get_base_ingredient_counts(subName, multiplier * quantity)

			for ingredientName, quantity in subResult.items():
				# If the ingredient already exists in the raw ingredients list, just add the quantity to that.
				# Otherwise we have a new dictionary entry 
				result[ingredientName] = result.get(ingredientName, 0) + quantity

		return result
# =============================================================================
# ==== DO NOT TOUCH ===========================================================
# =============================================================================

if __name__ == '__main__':
	app.run(debug=True, port=8080)
