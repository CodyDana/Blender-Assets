// ArmoryLab: V toggles first person / third person. See ArmoryViewToggleComponent.h.

#include "ArmoryViewToggleComponent.h"

#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "Engine/LocalPlayer.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GenericPlatform/GenericPlatformInputDeviceMapper.h"
#include "InputAction.h"
#include "InputKeyEventArgs.h"
#include "InputMappingContext.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

DEFINE_LOG_CATEGORY_STATIC(LogArmoryView, Log, All);

UArmoryViewToggleComponent::UArmoryViewToggleComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.bStartWithTickEnabled = true;
	PrimaryComponentTick.TickGroup = TG_PrePhysics;
}

ACharacter* UArmoryViewToggleComponent::GetCharacter() const
{
	return Cast<ACharacter>(GetOwner());
}

void UArmoryViewToggleComponent::BeginPlay()
{
	Super::BeginPlay();
	const UWorld* World = GetWorld();
	bSelfTest = World && World->IsGameWorld() && FParse::Param(FCommandLine::Get(), TEXT("AKViewToggleTest"));
	EnsureFirstPersonCamera();
	if (bStartInFirstPerson)
	{
		SetFirstPerson(true);
	}
	UE_LOG(LogArmoryView, Log, TEXT("AK_VIEWTOGGLE ready on %s (self-test %d)"), *GetNameSafe(GetOwner()), bSelfTest ? 1 : 0);
}

void UArmoryViewToggleComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (bIsFirstPerson)
	{
		SetFirstPerson(false);
	}
	Super::EndPlay(EndPlayReason);
}

void UArmoryViewToggleComponent::EnsureFirstPersonCamera()
{
	ACharacter* Character = GetCharacter();
	if (!Character || FirstPersonCamera)
	{
		return;
	}
	// the template's own cameras (FollowCamera on the CameraBoom): remembered so V can switch back to exactly them
	TArray<UCameraComponent*> Cameras;
	Character->GetComponents<UCameraComponent>(Cameras);
	for (UCameraComponent* Camera : Cameras)
	{
		ThirdPersonCameras.Add(Camera);
	}
	FirstPersonCamera = NewObject<UCameraComponent>(Character, TEXT("ArmoryFirstPersonCamera"));
	FirstPersonCamera->bAutoActivate = false;
	FirstPersonCamera->bUsePawnControlRotation = true;   // mouse look = the template's control rotation, unchanged
	FirstPersonCamera->SetFieldOfView(FirstPersonFOV);
	FirstPersonCamera->SetupAttachment(Character->GetCapsuleComponent());
	FirstPersonCamera->RegisterComponent();
	FirstPersonCamera->Deactivate();
}

void UArmoryViewToggleComponent::ToggleView()
{
	SetFirstPerson(!bIsFirstPerson);
}

void UArmoryViewToggleComponent::OnTogglePressed()
{
	ToggleView();
}

void UArmoryViewToggleComponent::SetFirstPerson(bool bFirstPerson)
{
	ACharacter* Character = GetCharacter();
	EnsureFirstPersonCamera();
	if (!Character || !FirstPersonCamera || bFirstPerson == bIsFirstPerson)
	{
		return;
	}
	USkeletalMeshComponent* Mesh = Character->GetMesh();
	UCharacterMovementComponent* Move = Character->GetCharacterMovement();
	if (bFirstPerson)
	{
		// eye height from the head bone, held fixed on the capsule (no head bob, no roll); the eyes sit EyeOffset from it
		float EyeZ = Character->BaseEyeHeight;
		if (Mesh && Mesh->GetBoneIndex(HeadBone) != INDEX_NONE)
		{
			const FVector Head = Mesh->GetBoneLocation(HeadBone, EBoneSpaces::WorldSpace);
			EyeZ = Character->GetCapsuleComponent()->GetComponentTransform().InverseTransformPosition(Head).Z;
		}
		FirstPersonCamera->SetRelativeLocation(FVector(EyeOffset.X, EyeOffset.Y, EyeZ + EyeOffset.Z));
		FirstPersonCamera->SetFieldOfView(FirstPersonFOV);
		for (const TWeakObjectPtr<UCameraComponent>& Camera : ThirdPersonCameras)
		{
			if (Camera.IsValid())
			{
				Camera->Deactivate();
			}
		}
		FirstPersonCamera->Activate(true);
		if (Mesh)
		{
			bSavedCastHiddenShadow = Mesh->bCastHiddenShadow;
			Mesh->SetOwnerNoSee(true);        // a clean view: no body or hair in front of the eyes
			Mesh->SetCastHiddenShadow(true);  // the body still casts its shadow
		}
		if (Move)
		{
			bSavedOrientToMovement = Move->bOrientRotationToMovement;
			Move->bOrientRotationToMovement = false;
		}
		bSavedUseControllerYaw = Character->bUseControllerRotationYaw;
		Character->bUseControllerRotationYaw = true;   // the body turns with the mouse, so strafing works as expected
	}
	else
	{
		FirstPersonCamera->Deactivate();
		for (const TWeakObjectPtr<UCameraComponent>& Camera : ThirdPersonCameras)
		{
			if (Camera.IsValid())
			{
				Camera->Activate(true);
			}
		}
		if (Mesh)
		{
			Mesh->SetOwnerNoSee(false);
			Mesh->SetCastHiddenShadow(bSavedCastHiddenShadow);
		}
		if (Move)
		{
			Move->bOrientRotationToMovement = bSavedOrientToMovement;
		}
		Character->bUseControllerRotationYaw = bSavedUseControllerYaw;
	}
	bIsFirstPerson = bFirstPerson;
	++ToggleCount;
	UE_LOG(LogArmoryView, Log, TEXT("AK_VIEWTOGGLE %s person (toggle %d)"), bIsFirstPerson ? TEXT("first") : TEXT("third"),
		ToggleCount);
}

float UArmoryViewToggleComponent::GetViewDistanceFromHead() const
{
	const ACharacter* Character = GetCharacter();
	if (!Character)
	{
		return -1.0f;
	}
	FVector View = FVector::ZeroVector;
	const APlayerController* PC = Cast<APlayerController>(Character->GetController());
	if (PC && PC->PlayerCameraManager)
	{
		View = PC->PlayerCameraManager->GetCameraLocation();
	}
	else if (bIsFirstPerson && FirstPersonCamera)
	{
		View = FirstPersonCamera->GetComponentLocation();
	}
	else
	{
		return -1.0f;
	}
	const USkeletalMeshComponent* Mesh = Character->GetMesh();
	const FVector Head = (Mesh && Mesh->GetBoneIndex(HeadBone) != INDEX_NONE)
		? Mesh->GetBoneLocation(HeadBone, EBoneSpaces::WorldSpace)
		: Character->GetPawnViewLocation();
	return FVector::Dist(View, Head);
}

void UArmoryViewToggleComponent::UpdateInputBinding()
{
	const APawn* Pawn = Cast<APawn>(GetOwner());
	UInputComponent* Input = Pawn ? Pawn->InputComponent.Get() : nullptr;
	APlayerController* PC = Pawn ? Cast<APlayerController>(Pawn->GetController()) : nullptr;
	if (!Input || !PC || !PC->IsLocalController())
	{
		BoundInputComponent.Reset();
		return;
	}
	if (BoundInputComponent.Get() == Input)
	{
		return;
	}
	UEnhancedInputComponent* Enhanced = Cast<UEnhancedInputComponent>(Input);
	UEnhancedInputLocalPlayerSubsystem* Subsystem =
		ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PC->GetLocalPlayer());
	if (!Enhanced || !Subsystem)
	{
		return;
	}
	const UInputAction* Action = ToggleViewAction;
	const UInputMappingContext* Context = ToggleViewContext;
	if (!Action || !Context)
	{
		// no assets assigned: a transient action on FallbackKey (V), so the toggle always works
		if (!RuntimeAction)
		{
			RuntimeAction = NewObject<UInputAction>(this, TEXT("IA_ToggleView_Runtime"));
			RuntimeAction->ValueType = EInputActionValueType::Boolean;
			RuntimeContext = NewObject<UInputMappingContext>(this, TEXT("IMC_ArmoryView_Runtime"));
			RuntimeContext->MapKey(RuntimeAction, FallbackKey);
		}
		Action = RuntimeAction;
		Context = RuntimeContext;
		UE_LOG(LogArmoryView, Warning, TEXT("AK_VIEWTOGGLE no IA_ToggleView / IMC_ArmoryView assigned: runtime mapping on %s"),
			*FallbackKey.ToString());
	}
	if (!Subsystem->HasMappingContext(Context))
	{
		Subsystem->AddMappingContext(Context, ToggleViewContextPriority);
	}
	Enhanced->BindAction(Action, ETriggerEvent::Started, this, &UArmoryViewToggleComponent::OnTogglePressed);
	BoundInputComponent = Input;
	UE_LOG(LogArmoryView, Log, TEXT("AK_VIEWTOGGLE bound %s (context %s, priority %d)"), *GetNameSafe(Action),
		*GetNameSafe(Context), ToggleViewContextPriority);
}

void UArmoryViewToggleComponent::TickComponent(float DeltaTime, ELevelTick TickType,
	FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	UpdateInputBinding();
	if (bSelfTest && BoundInputComponent.IsValid())
	{
		TickSelfTest(DeltaTime);
	}
}

void UArmoryViewToggleComponent::PressKeyForTest(bool bPressed)
{
	ACharacter* Character = GetCharacter();
	APlayerController* PC = Character ? Cast<APlayerController>(Character->GetController()) : nullptr;
	if (!PC)
	{
		return;
	}
	// the real key through the player controller, as the keyboard would deliver it (Enhanced Input then maps it)
	const FInputDeviceId Device = IPlatformInputDeviceMapper::Get().GetPrimaryInputDeviceForUser(PC->GetPlatformUserId());
	const FInputKeyEventArgs Args = FInputKeyEventArgs::CreateSimulated(EKeys::V, bPressed ? IE_Pressed : IE_Released,
		bPressed ? 1.0f : 0.0f, -1, Device);
	const bool bHandled = PC->InputKey(Args);
	UE_LOG(LogArmoryView, Log, TEXT("AK_VIEWTOGGLE test key V %s handled=%d"), bPressed ? TEXT("down") : TEXT("up"),
		bHandled ? 1 : 0);
}

void UArmoryViewToggleComponent::TickSelfTest(float DeltaTime)
{
	ACharacter* Character = GetCharacter();
	APlayerController* PC = Character ? Cast<APlayerController>(Character->GetController()) : nullptr;
	if (!PC)
	{
		return;
	}
	TestClock += DeltaTime;
	TestStageClock += DeltaTime;
	auto Next = [this]() { ++TestStage; TestStageClock = 0.0f; };
	auto Yaw = [PC](float Degrees) {
		FRotator R = PC->GetControlRotation();
		R.Yaw += Degrees;
		PC->SetControlRotation(R);
	};
	switch (TestStage)
	{
	case 0:   // settle in third person at the PlayerStart
		if (TestStageClock > 3.0f)
		{
			TestThirdCm = GetViewDistanceFromHead();
			const UInputAction* Action = ToggleViewAction ? ToggleViewAction.Get() : RuntimeAction.Get();
			if (UEnhancedInputLocalPlayerSubsystem* Sub =
				ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PC->GetLocalPlayer()))
			{
				for (const FKey& Key : Sub->QueryKeysMappedToAction(Action))
				{
					TestKeys += (TestKeys.IsEmpty() ? TEXT("") : TEXT("+")) + Key.ToString();
				}
			}
			UE_LOG(LogArmoryView, Log, TEXT("AK_VIEWTOGGLE test third person: view %.1f cm from the head; keys [%s]"),
				TestThirdCm, *TestKeys);
			PressKeyForTest(true);
			Next();
		}
		break;
	case 1:
		if (TestStageClock > 0.1f) { PressKeyForTest(false); Next(); }
		break;
	case 2:   // first person
		if (TestStageClock > 1.0f)
		{
			TestFirstCm = GetViewDistanceFromHead();
			TestFirstFlag = bIsFirstPerson;
			UE_LOG(LogArmoryView, Log, TEXT("AK_VIEWTOGGLE test after V: first=%d view %.1f cm from the head"),
				TestFirstFlag ? 1 : 0, TestFirstCm);
			Next();
		}
		break;
	case 3:   // walk in through the entrance (the courtyard route is clear along the path)
		Character->AddMovementInput(Character->GetActorForwardVector(), 1.0f);
		if (TestStageClock > 2.5f) { Next(); }
		break;
	case 4:   // look round once in first person
		Yaw(90.0f * DeltaTime);
		if (TestStageClock > 4.0f) { PressKeyForTest(true); Next(); }
		break;
	case 5:
		if (TestStageClock > 0.1f) { PressKeyForTest(false); Next(); }
		break;
	case 6:   // back in third person
		if (TestStageClock > 1.0f)
		{
			TestBackCm = GetViewDistanceFromHead();
			TestBackFlag = bIsFirstPerson;
			UE_LOG(LogArmoryView, Log, TEXT("AK_VIEWTOGGLE test after V again: first=%d view %.1f cm from the head"),
				TestBackFlag ? 1 : 0, TestBackCm);
			Next();
		}
		break;
	case 7:   // look round once in third person
		Yaw(90.0f * DeltaTime);
		if (TestStageClock > 4.0f) { Next(); }
		break;
	case 8:
		if (TestStageClock > 2.0f)
		{
			TArray<FString> Keys;
			TestKeys.ParseIntoArray(Keys, TEXT("+"));
			const bool bKeyV = Keys.Contains(TEXT("V"));
			const bool bPassed = bKeyV && TestThirdCm > 150.0f && TestFirstFlag && TestFirstCm >= 0.0f &&
				TestFirstCm < 40.0f && !TestBackFlag && TestBackCm > 150.0f && ToggleCount >= 2;
			UE_LOG(LogArmoryView, Display,
				TEXT("AK_STEP_DONE fptest passed=%s third_cm=%.1f first_cm=%.1f back_cm=%.1f keys=%s toggles=%d secs=%.1f"),
				bPassed ? TEXT("True") : TEXT("False"), TestThirdCm, TestFirstCm, TestBackCm, *TestKeys, ToggleCount,
				TestClock);
			Next();
			PC->ConsoleCommand(TEXT("quit"));
		}
		break;
	default:
		break;
	}
}
