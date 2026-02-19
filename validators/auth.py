from marshmallow import Schema, fields


# consulter la doc de marshamallow pour savoir comment on utilise

# Schémas de validation avec Marshmallow
class RegisterSchema(Schema):
    username = fields.Str(required=True, validate=lambda x: len(x) >= 3)
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=lambda x: len(x) >= 6)
    name = fields.Str(required=True, error_messages={"error": "Votre nom est requis"})

class LoginSchema(Schema):
    username = fields.Str(required=True)
    password = fields.Str(required=True)
