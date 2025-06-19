-- Oski Rubricon User Addition Script
-- Adds multiple UT Southwestern users with password '1234'
-- Compatible with Supabase/PostgreSQL authentication

-- Add existing user (already provided)
INSERT INTO users (email, password_hash, created_at)
VALUES (
  'sahaj.satani@utsouthwestern.edu',
  crypt('1234', gen_salt('bf')),
  NOW()
);

-- Add new users
INSERT INTO users (email, password_hash, created_at)
VALUES (
  'arjan.suri@utsouthwestern.edu',
  crypt('1234', gen_salt('bf')),
  NOW()
);

INSERT INTO users (email, password_hash, created_at)
VALUES (
  'Aarash.Zakeri@UTSouthwestern.edu',
  crypt('1234', gen_salt('bf')),
  NOW()
);

INSERT INTO users (email, password_hash, created_at)
VALUES (
  'David.Hein@UTSouthwestern.edu',
  crypt('1234', gen_salt('bf')),
  NOW()
);

INSERT INTO users (email, password_hash, created_at)
VALUES (
  'Dhanush.Jain@UTSouthwestern.edu',
  crypt('1234', gen_salt('bf')),
  NOW()
);

INSERT INTO users (email, password_hash, created_at)
VALUES (
  'Andrew.Jamieson@UTSouthwestern.edu',
  crypt('1234', gen_salt('bf')),
  NOW()
);

INSERT INTO users (email, password_hash, created_at)
VALUES (
  'Similoluwa.Okunowo@UTSouthwestern.edu',
  crypt('1234', gen_salt('bf')),
  NOW()
);

-- Alternative bulk insert approach (more efficient)
-- Uncomment if you prefer to insert all at once:
/*
INSERT INTO users (email, password_hash, created_at)
VALUES 
  ('sahaj.satani@utsouthwestern.edu', crypt('1234', gen_salt('bf')), NOW()),
  ('arjan.suri@utsouthwestern.edu', crypt('1234', gen_salt('bf')), NOW()),
  ('Aarash.Zakeri@UTSouthwestern.edu', crypt('1234', gen_salt('bf')), NOW()),
  ('David.Hein@UTSouthwestern.edu', crypt('1234', gen_salt('bf')), NOW()),
  ('Dhanush.Jain@UTSouthwestern.edu', crypt('1234', gen_salt('bf')), NOW()),
  ('Andrew.Jamieson@UTSouthwestern.edu', crypt('1234', gen_salt('bf')), NOW()),
  ('Similoluwa.Okunowo@UTSouthwestern.edu', crypt('1234', gen_salt('bf')), NOW());
*/ 