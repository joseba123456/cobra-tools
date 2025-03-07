from generated.base_enum import UintEnum


class CollisionType(UintEnum):
	Sphere = 0
	BoundingBox = 1
	Capsule = 2
	Cylinder = 3
	ConvexHull = 7
	ConvexHullPC = 8
	# widgetball_test.mdl2, Ball_Hitcheck not supported, seems to be another collision mesh used in JWE redwoods
	MeshCollision = 10
	# widgetball_test.mdl2, Ball_Hitcheck not supported, seems to be another collision mesh used in JWE redwoods
	UnkRhino = 11
