WbFeedback quiet OFF;
WbExport -file='C:\Users\jpetit\O365\GROUPE~1\DATOSI~3\bdd\exports\productos.csv' -type=text -delimiter=';' -header=true -quoteChar='"';
SELECT 
                p.CODESAISON,
                cp3.LIBCLASSPROD3,
                a.CODEPRODUIT, 
                a.CODECOLORIS,
                p.NOMPRODUIT,
                c.LIBCOLORIS,
                a.CODEBARRES AS EAN,
                a.CODEINTERNEARTICLE

            FROM STORELAND.ARTICLES a 
                                            
            JOIN STORELAND.PRODUITS p
                ON a.CODEPRODUIT = p.CODEPRODUIT
            
            LEFT JOIN STORELAND.COLORIS c
                ON a.CODECOLORIS = c.CODECOLORIS
            
            LEFT JOIN STORELAND.CLASSPROD3 cp3
                ON p.CODECLASSPROD3 = cp3.CODECLASSPROD3

            LEFT JOIN STORELAND.CLASSPROD2 cp2
                ON cp3.CODECLASSPROD2 = cp2.CODECLASSPROD2

            LEFT JOIN STORELAND.CLASSPROD1 cp1
                ON cp2.CODECLASSPROD1 = cp1.CODECLASSPROD1

            WHERE p.CODESAISON IN ('E23','H23','E24','H24','E25','H25','E26','H26');
EXIT;
