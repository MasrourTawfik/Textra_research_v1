Building and Exploring the Reinforcement Learning Knowledge Graph
==================================================================

Overview
---------


Our knowledge graph represents mappings of the RL field , encompassing:
- 227 Core Concepts
- 67 Distinct Algorithms
- 82 Research Papers
- 50+ Methodological Approaches
- 19 Frameworks
- 13 Algorithm Variants
- Multiple Specialized Domains

.. figure:: ../Images/graph.png
    :align: center
    :alt: Knowledge Graph Overview
Knowledge Graph Overview


This visualization reveals the dense interconnections between different elements of reinforcement learning.


Neo4j Knowledge Graph Interface: A Visual Guide
-----------------------------------------------

.. figure:: ../Images/kg.png
   :alt: Neo4j Knowledge Graph Interface Overview
   :width: 100%
   :align: center

   Neo4j Knowledge Graph Interface showing the main components and visualization tools

Interface Components
~~~~~~~~~~~~~~~~~~~~

1. NEO4J Query Bar
   * Where Cypher queries are entered to interact with the graph database
   * Currently showing "MATCH(n) RETURN n" which displays all nodes

2. Export Tools
   * Provides export functionality in multiple formats:
     - JSON
     - PNG
     - SVG
     - CSV

3. Left Sidebar Tools
   * Graph: Visual graph view selector
   * Properties View: Displays detailed node and relationship properties in JSON format
   * Text: Text view option
   * Code: Code view selector

4. Node Labels Panel
   * Displays all node types with their respective counts
   * Color-coded categories including:
     - Concept: 227 nodes
     - Algorithm: 67 nodes
     - Paper: 82 nodes
   * Contains 15 distinct node types

5. Relationship Types Panel
   * Shows relationship varieties between nodes
   * Displays 50 out of 245 total relationship types
   * Key relationships include:
     - REFERENCED_IN (186 instances)
     - PROVIDES_BASIS_FOR (22 instances)

