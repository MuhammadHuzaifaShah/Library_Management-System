from fastapi import FastAPI, Response, status,HTTPException,Depends,APIRouter
from sqlalchemy.orm import Session
from ..database import get_db
from ..import models,schemas,utils,outh2

router=APIRouter(
    prefix="/users",
    tags=['users']
)

@router.post("/", status_code=status.HTTP_201_CREATED,response_model=schemas.UserResponse)
def create_user(user:schemas.UserCreate, db:Session= Depends(get_db)):
    hashed_password= utils.hash(user.password)
    user.password =hashed_password
    new_user =models.User(**user.model_dump())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.get("/", status_code=status.HTTP_201_CREATED,response_model=list[schemas.UserResponse])
def get_all_user(db:Session= Depends(get_db)):
    users=db.query(models.User).all()
    return users

@router.get("/me",response_model=schemas.UserCreate)
def get_current_user_info(current_user: models.User=Depends(outh2.get_current_user)):

    return  current_user

@router.get("/{id}", response_model=schemas.UserResponse)
def get_Users(id: int,db:Session= Depends(get_db)):
    user=db.query(models.User).filter(models.User.id==id).first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                             detail=f"post with id: {id} does not exist")
    
    return user


@router.delete("/{id}",status_code=status.HTTP_204_NO_CONTENT)
def delete_user(id:int,db:Session=Depends(get_db)):
    user=db.query(models.User).filter(models.User.id==id).first()
    

    if user==None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                             detail=f"post with id: {id} does not exist")
    
    db.delete(user)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{id}",response_model=schemas.UserCreate)
def update_user(id: int, user: schemas.UserCreate,db:Session= Depends(get_db)):

    user_query=db.query(models.User).filter(models.User.id==id).first()

    if user_query==None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                             detail=f"post with id: {id} does not exist")
    
    user_query.name=user.name
    user_query.email=user.email
    user_query.password=utils.hash(user.password)

    db.commit()
    db.refresh(user_query)

    return  user_query



