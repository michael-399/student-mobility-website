# Conceptual Entities

## User

Represents a person who can authenticate and use the platform.

Shared attributes:

- user identifier
- email address
- password hash
- first name
- last name
- user role

The plaintext password is never stored. The application hashes passwords using
Argon2id. The Argon2 library generates a unique random salt for each password and
includes the salt and algorithm parameters in the encoded hash stored in
`password_hash`.

# Preliminary Logical Schema

## USER_ACCOUNT

| Attribute | Preliminary type | Constraints |
|---|---|---|
| `user_id` | `BIGINT` | Primary key |
| `email` | `VARCHAR(255)` | Not null, unique |
| `password_hash` | `TEXT` | Not null |
| `first_name` | `VARCHAR(100)` | Not null |
| `last_name` | `VARCHAR(100)` | Not null |
| `user_role` | `USER_ROLE` | Not null |

Allowed `USER_ROLE` values:

- `student`
- `coordinator`
- `office_staff`

Authentication is performed in Python rather than in PostgreSQL:

1. Registration: hash the plaintext password with Argon2id and store only the
   resulting encoded hash.
2. Login: retrieve the encoded hash by email and ask the Argon2 library to verify
   the submitted plaintext password against it.
3. Never manually extract, concatenate, or compare the salt and password.

## HostInstitution 

 Represents a partner university abroad that can host students during an Overseas mobility.

Shared attributes: 

- UNI identifier
- UNI name 
- UNI Contact Email
- Country
- City 
- Quota / Available slots 

# Preliminary Logical Schema 

## HOST_INSTITUTION

| Attribute | Preliminary type | Constraints |
|---|---|---|
| `institution_id` | `BIGINT` | Primary key |
| `name` | `VARCHAR(255)` | Not null |
| `country` | `VARCHAR(100)` | Not null |
| `city` | `VARCHAR(100)` | Not null |
| `contact_email` | `VARCHAR(255)` | Optional |
| `is_active` | `BOOLEAN` | Not null, default true |

