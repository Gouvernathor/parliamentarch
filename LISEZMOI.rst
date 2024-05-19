Parliamentarch
==============

Module utilitaire permettant la génération de diagrammes parlementaires en
hémicycles.

Base de maths
-------------

L'idée est de placer un certain nombre de sièges en forme d'hémicycle. La forme
recherchée peut être définie comme suit :

- Prenez deux cercles concentriques tels que le rayon du cercle extérieur soit
  le double du rayon du cercle intérieur.
- Prenez l'aire séparant les deux cercles, appelée un anneau.
- Divisez cet anneau en deux par un diamètre du cercle extérieur.

Le résultat est un hémicycle. Maintenant, pour placer les sièges tels qu'ils
suivent la forme de l'hémicycle :

- L'hémicycle rentre dans un rectangle de proportions 2:1, pris en orientation
  paysage avec le diamètre de coupe en bas (les coins supérieur gauche et
  supérieur droit du rectangle sont vides).
- Les sièges sont placés en rangées, tel que :
  - Les rangées sont des arcs de cercle, concentriques avec les arcs de cercle
    formant l'hémicycle.
  - La différence entre les rayons de deux rangées consécutives est une
    constante appelée "épaisseur de rangée".
  - Les sièges sont des cercles (ou des disques) de rayon égal. Ce rayon divisé
    par la moitié de l'épaisseur de rangée donne le "ratio de rayon de siège".
  - Le centre d'un siège est placé sur l'arc de la rangée dont il fait partie.
  - Dans une rangée donnée, la distance entre deux sièges voisins est constante.
  - La rangée la plus intérieure est l'arc de cercle le plus petit ayant servi à
    définir l'hémicycle.
  - Le rayon de la rangée la plus extérieure est égal au rayon du cercle
    extérieur moins la moitié de l'épaisseur de rangée, de manière à ce qu'aucun
    siège ne puisse mordre l'arc de cercle extérieur.
  - Les sièges les plus bas de chaque rangée, qui sont le premier et le dernier
    siège de la rangée, sont tangents au côté inférieur du rectangle.
  - Quand une rangée ne contient qu'un siège, la règle précédente ne s'applique
    pas et le siège est placé au milieu horizontal du diagramme.

En conséquence, il existe un nombre maximum de sièges que l'on peut placer dans
un diagramme contenant un nombre donné de rangées. Pour des nombres de sièges
inférieurs à cette valeur, il existe plusieurs stratégies pour distribuer les
sièges entre les rangées.

À noter : les maths ci-dessus s'appliquent dans le cas classique d'un hémicycle
s'étendant sur 180°. En spécifiant un angle plus petit, l'anneau initial doit
être coupé suivant deux rayons du cercle extérieur. Pour le placement des
sièges, ce qui s'appliquait au côté inférieur du rectangle s'applique alors aux
deux rayons de coupe.

Règles ajustables
-----------------

Comme sous-entendu plus haut, plusieurs paramètres peuvent être ajustés pour
changer la forme de l'hémicycle.

- L'angle sur lequel s'étend l'hémicycle peut être réduit en-dessous de 180°
  (les valeurs plus grandes ne sont pas supportées). Cependant, le cas où
  l'angle est suffisament aigü pour empêcher une rangée de contenir un seul
  siège n'est pas supporté, peut donner des résultats incorrects, et pourra
  causer des erreurs dans des versions futures.
- Le nombre de rangées peut être augmenté par rapport au minimum nécessaire pour
  contenir le nombre de sièges donné.
- Le ratio de rayon de siège peut être ajusté entre 0 et 1, avec les sièges
  touchant leurs voisins latéraux avec une valeur de 1.
- Tant que le nombre de sièges n'est pas le nombre maximum que le nombre de
  rangées peut contenir, différentes stratégies peuvent être suivies pour les
  répartir entre les rangées.

Contenu du module principal
---------------------------

Ces éléments se trouvent dans le module ``parliamentarch``.

``SeatData``

Cette classe est définie et expliquée dans le sous-module SVG ci-dessous, mais
il est exposé au sein du module principal.

``write_svg_from_attribution(file, attrib, **kwargs)``

Cette fonction écrit un fichier SVG représentant un hémicycle. Les paramètres
sont les suivants :

- ``file: str|io.TextIOBase`` : un fichier ouvert en mode texte, ou le chemin
  vers le fichier sur lequel écrire. Si un chemin est fourni, le fichier sera
  créé si il n'existe pas, et sera écrasé sinon.
- ``attrib: dict[SeatData, int]`` : un dictionnaire d'objets SeatData
  s'appliquant à un ensemble de sièges présents dans l'hémicycle, vers le nombre
  de sièges auxquels l'objet s'applique. Typiquement, chaque objet correspond à
  un parti ou un groupe. L'ordre des clés a un sens, et les éléments seront
  disposés de gauche à droite dans l'hémicycle.
- ``**kwargs`` : tous les paramètres optionnels acceptés par
  ``parliamentarch.geometry.get_seats_centers`` ou par
  ``parliamentarch.svg.write_svg`` peuvent être passés à cette fonction.

``get_svg_from_attribution(attrib, **kwargs) -> str``

Au lieu d'écrire dans un fichier, cette fonction renvoie le contenu au format
SVG dans une chaîne de caractères. Les autres paramètres sont identiques.

Interface en ligne de commande
------------------------------

Voir ``py -m parliamentarch -h`` pour la liste des paramètres.

Contenu du sous-module geometry
-------------------------------

Ces éléments se trouvent dans le sous-module ``parliamentarch.geometry``.

``get_nrows_from_nseats(nseats: int, span_angle: float = 180.) -> int``

Renvoie le nombre minimum de rangées nécessaires pour contenir un nombre donné
de sièges dans un diagramme s'étendant sur un angle donné.

``get_rows_from_nrows(nrows: int, span_angle: float = 180.) -> List[int]``

À partir d'un nombre de rangées donné (et d'un angle d'étendue), renvoie une
liste du nombre maximum de sièges que chaque rangée peut contenir, de
l'intérieur vers l'extérieur. La liste est croissante et sa longueur est égale au nombre de rangées.

``FillingStrategy``

Énumération des différentes stratégies de répartition des sièges entre les
rangées. Les stratégies implémentées sont les suivantes :

- ``FillingStrategy.DEFAULT`` : Répartit les sièges de manière proportionnelle
  au nombre maximum de sièges que chaque rangée peut contenir. Le résultat rend
  la distance latérale entre des sièges voisins similaire entre les rangées.
- ``FillingStrategy.EMPTY_INNER`` : Sélectionne le nombre minimal de rangées
  extérieures nécessaires pour contenir le nombre de sièges donné, puis
  distribue les sièges de manière proportionnelle entre ces rangées. En fonction
  du nombre de sièges et de rangées, soit des rangées intérieures resteront
  vides, soit le résultat sera identique à la stratégie ``DEFAULT``. Sans
  compter les rangées vides, la distance entre des sièges voisins est à la fois
  minimale, et proche d'une rangée à l'autre.
- ``FillingStrategy.OUTER_PRIORITY`` : Remplit les rangées à leur capacité
  maximale, de l'extérieur vers l'intérieur. Le résultat est qu'avec un nombre
  donné de rangées, ajouter un siège ne modifie qu'une seule rangée.

``get_seats_centers(nseats: int, *, min_nrows: int = 0, span_angle: float = 180., seat_radius_factor: float = 1., filling_strategy: FillingStrategy = FillingStrategy.DEFAULT) -> List[Tuple[float, float]]``

La fonction principale. En-dehors des paramètres évidents ou équivalents aux fonctions précédentes :

- ``min_nrows`` : le nombre minimum de rangées à utiliser. Uniquement pris en
  compte si la valeur est supérieure au nombre de rangées nécessaires pour
  contenir le nombre de sièges donné.
- ``seat_radius_factor`` : le ratio de rayon de siège, égal au rayon du siège
  divisé par l'épaisseur de rangée. Par défaut, à 1, les sièges peuvent toucher
  leurs voisins.

La fonction renvoie un objet similaire à un dictionnaire représentant l'ensemble
des sièges. Les clés sont ``(x, y)``, les coordonnées cartésiennes du centre du
siège. Les coordonnées partent du coin inférieur gauche du rectangle, avec l'axe
x vers la droite et l'axe y vers le haut. Le rayon de l'arc extérieur (égal à la
hauteur et à la moitié de la largeur du rectangle) est 1, donc x va de 0 à 2 et
y de 0 à 1.

La valeur pour chaque clé est l'angle, en radian, depuis le point le plus
extérieur et à droite de l'arc d'anneau, vers le centre des arcs, jusqu'au
centre du siège.

De plus, la valeur de retour contient les attributs suivants :

- ``di.seat_actual_radius`` : le rayon des sièges, dans la même unité que les
  coordonnées.
- ``di.nrows`` : comme passé à la fonction.
- ``di.seat_radius_factor`` : comme passé à la fonction.

Appeler ``sorted(di, key=di.get, reverse=True)`` renvoie la liste des sièges
triée de gauche à droite.

Contenu du sous-module SVG
--------------------------

Ces éléments se trouvent dans le sous-module ``parliamentarch.svg``.

``SeatData(data, color, border_size=0, border_color="#000")``

Une classe informant la représentation d'un siège ou d'un groupe de sièges.

- ``data: str`` : métadonnées à propos du groupe de sièges, qui finira dans le
  fichier SVG. Typiquement le nom du parti ou de l'élu.
- ``color: Color`` : la couleur de remplissage du cercle représentant le siège.
  Accepte divers formats de données : une string "#RGB", "#RRGGBB", "#RGBA" ou
  "#RRGGBBAA", un ``tuple[int, int, int]`` RGB, ou un
  ``tuple[int, int, int, int]`` RGBA avec des entiers entre 0 et 255. Les noms
  de couleurs CSS sont aussi acceptés.
- ``border_size: float`` : la taille de la bordure du cercle représentant le
  siège. (à documenter avec plus de détails)
- ``border_color: Color`` : la couleur de la bordure.

``write_svg(file, seat_centers, seat_actual_radius, *, canvas_size=175, margins=5., write_number_of_seats=True, font_size_factor=...)``

Cette fonction écrit un fichier SVG représentant un hémicycle. Les paramètres
sont les suivants :

- ``file: str|io.TextIOBase`` : un fichier ouvert en mode texte, ou le chemin
  vers le fichier sur lequel écrire. Si un chemin est fourni, le fichier sera
  créé si il n'existe pas, et sera écrasé sinon.
- ``seat_centers: dict[tuple[float, float], SeatData]`` : un dictionnaire des
  coordonnées (x, y) des centres des sièges vers des objets SeatData.
- ``seat_actual_radius: float`` : le rayon des sièges, tel que renvoyé par
  ``get_seats_centers``.
- ``canvas_size: float`` : la hauteur du rectangle 2:1 dans lequel l'hémicycle
  est inscrit.
- ``margins: float|tuple[float, float]|tuple[float, float, float, float]`` : les
  marges autour de ce rectangle. Si quatre valeurs sont données, elles sont la
  marge gauche, supérieure, droite et inférieure, dans cet ordre. Si deux
  valeurs sont données, elles sont la marge horizontale et la marge verticale,
  dans cet ordre. Si une seule valeur est donnée, elle est utilisée pour les
  quatre marges.
- ``write_number_of_seats: bool`` : si le nombre total de sièges est inscrit en
  bas au milieu du diagramme - au niveau du perchoir.
- ``font_size_factor: float`` : un facteur à modifier pour changer la taille de
  police du nombre de sièges. La valeur par défaut est proche de 0.2. Garder
  cette valeur constante gardera la taille de police à la même échelle quand
  ``canvas_size`` change.

``write_grouped_svg(file, seat_centers_by_group, *args, **kwargs)``

Cette fonction prend d'une manière différente la relation entre les sièges et
les objets SeatData, une manière bien plus optimisée tant sur la taille du
fichier SVG généré que sur le temps de calcul. Les autres paramètres sont
identiques.

- ``seat_centers_by_group: dict[SeatData, list[tuple[float, float]]]`` : un
  dictionnaire des objets SeatData d'un groupe de sièges vers une liste de
  coordonnées (x, y) des centres des sièges telles que fournies par la fonction
  ``get_seats_centers``.

Ces deux fonctions ont des équivalents qui renvoient le contenu du fichier SVG
sous forme de chaîne de caractères. Elles prennent les mêmes paramètres, sauf
``file``, et elles s'appellent ``get_svg`` et ``get_grouped_svg``.

``dispatch_seats(group_seats, seats) -> dict[SeatData, list[S]]``

Une fonction qui aide le passage de ``parliamentarch.get_seats_centers`` à
``write_grouped_svg`` :

- ``group_seats: dict[SeatData, int]`` : un dictionnaire de l'objet SeatData
  d'un groupe de sièges vers le nombre de sièges dans ce groupe. L'ordre des
  clés compte.
- ``seats: Iterable[S]`` : un itérable de sièges dans n'importe quel format,
  typiquement des tuples (x, y). La taille de l'itérable doit être égale à la
  somme des valeurs de ``group_seats``. L'ordre des données compte.

Typiquement les groupes sont ordonnés de gauche à droite, et les sièges sont
ordonnés de gauche à droite. ``sorted(di, key=di.get, reverse=True)`` peut
aider.

SeatData et dispatch_seats peuvent être déplacées dans un autre module dans une
version future.
